"""
Embedding & Reranker service.

Serves two capabilities from a single FastAPI process:

  POST /embed   — Generate embeddings (MrBERT or Qwen3-Embedding-0.6B)
  POST /rerank  — Cross-encoder reranking (Qwen3-Reranker-0.6B, optional)
  GET  /health  — Health check

The embedding model is always loaded. The reranker model is loaded only when
RERANKER_MODEL_PATH points to an existing directory with model files.

Both models share the same GPU and process, avoiding the overhead of a second
Docker container.

Pooling strategy for embeddings is configurable via POOLING_STRATEGY env var:
  - "mean"       : Mean pooling over all token embeddings (MrBERT default)
  - "last_token" : Last-token pooling with left-padding (Qwen3 default)
"""

import logging
import os
from contextlib import asynccontextmanager

import torch
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from transformers import AutoModel, AutoModelForCausalLM, AutoTokenizer

logger = logging.getLogger("embedding-service")
logging.basicConfig(level=logging.INFO)

# ── Configuration ────────────────────────────────────────────────────────────

MODEL_PATH = os.environ.get("MODEL_PATH", "/app/model")
RERANKER_MODEL_PATH = os.environ.get("RERANKER_MODEL_PATH", "/app/reranker_model")
DEVICE = os.environ.get("DEVICE", "cpu")
POOLING_STRATEGY = os.environ.get("POOLING_STRATEGY", "mean")
MAX_LENGTH = int(os.environ.get("MAX_LENGTH", "8192"))
RERANKER_MAX_LENGTH = int(os.environ.get("RERANKER_MAX_LENGTH", "8192"))
RERANKER_BATCH_SIZE = int(os.environ.get("RERANKER_BATCH_SIZE", "4"))

# ── Global references set during startup ─────────────────────────────────────

# Embedding model
embed_tokenizer = None
embed_model = None

# Reranker model (optional)
reranker_tokenizer = None
reranker_model = None
reranker_yes_token_id = None
reranker_no_token_id = None
reranker_available = False

device = None


# ── Device resolution ────────────────────────────────────────────────────────

def _resolve_device(requested: str) -> torch.device:
    """Resolve the compute device, falling back to CPU if CUDA is unavailable."""
    if requested == "cuda" and torch.cuda.is_available():
        logger.info("CUDA is available — using GPU")
        return torch.device("cuda")
    if requested == "cuda":
        logger.warning("CUDA requested but not available — falling back to CPU")
    return torch.device("cpu")


# ── Embedding pooling functions ──────────────────────────────────────────────

def mean_pooling(model_output: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
    """
    Mean pooling: average all token embeddings weighted by the attention mask.
    Used by MrBERT (classifier_pooling: "mean").
    """
    token_embeddings = model_output[0]  # (batch, seq_len, hidden_dim)
    mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    sum_embeddings = torch.sum(token_embeddings * mask_expanded, dim=1)
    sum_mask = torch.clamp(mask_expanded.sum(dim=1), min=1e-9)
    return sum_embeddings / sum_mask


def last_token_pooling(model_output: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
    """
    Last-token pooling: extract the hidden state of the last non-padding token.
    Used by Qwen3-Embedding with left-padding (last token = EOS).
    """
    token_embeddings = model_output[0]  # (batch, seq_len, hidden_dim)
    # With left-padding, the last real token is at the rightmost position
    # Find the index of the last 1 in attention_mask per sequence
    seq_lengths = attention_mask.sum(dim=1)  # noqa: F841
    # With left-padding the last token is always the rightmost, so just take [:, -1, :]
    return token_embeddings[:, -1, :]


_POOLING_FN = {
    "mean": mean_pooling,
    "last_token": last_token_pooling,
}


# ── Reranker scoring ────────────────────────────────────────────────────────

def _format_rerank_pair(query: str, document: str, instruction: str) -> str:
    """Format a query-document pair for the cross-encoder."""
    return f"<Instruct>: {instruction}\n<Query>: {query}\n<Document>: {document}"


def _score_pairs(pairs_text: list[str], batch_size: int = RERANKER_BATCH_SIZE) -> list[float]:
    """Score pairs using the cross-encoder. Returns relevance probabilities (0-1)."""
    all_scores = []

    for i in range(0, len(pairs_text), batch_size):
        batch = pairs_text[i : i + batch_size]

        conversations = []
        for text in batch:
            conversations.append([
                {
                    "role": "system",
                    "content": (
                        "Judge whether the Document meets the requirements based on the "
                        "Query and the Instruct provided. Note that the answer can only "
                        'be "yes" or "no".'
                    ),
                },
                {"role": "user", "content": text},
            ])

        inputs = reranker_tokenizer.apply_chat_template(
            conversations,
            padding=True,
            truncation=True,
            max_length=RERANKER_MAX_LENGTH,
            return_tensors="pt",
            return_dict=True,
            tokenize=True,
            add_generation_prompt=True,
        )

        # Append thinking tokens: <think>\n\n</think>\n\n
        think_start = reranker_tokenizer.encode("<think>", add_special_tokens=False)
        think_end = reranker_tokenizer.encode("\n\n</think>", add_special_tokens=False)
        newlines = reranker_tokenizer.encode("\n\n", add_special_tokens=False)
        suffix_tokens = think_start + newlines + think_end + newlines
        suffix_tensor = torch.tensor([suffix_tokens], device=device).expand(len(batch), -1)

        input_ids = torch.cat([inputs["input_ids"].to(device), suffix_tensor], dim=1)
        attention_mask = torch.cat(
            [inputs["attention_mask"].to(device), torch.ones_like(suffix_tensor)],
            dim=1,
        )

        with torch.no_grad():
            outputs = reranker_model(input_ids=input_ids, attention_mask=attention_mask)

        logits = outputs.logits[:, -1, :]
        yes_no_logits = logits[:, [reranker_yes_token_id, reranker_no_token_id]]
        scores = torch.softmax(yes_no_logits, dim=-1)[:, 0]  # P(yes)

        all_scores.extend(scores.cpu().float().tolist())

        # Free GPU memory between batches to avoid fragmentation
        del input_ids, attention_mask, outputs, logits, yes_no_logits, scores
        if device.type == "cuda":
            torch.cuda.empty_cache()

    return all_scores


# ── Lifespan ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load embedding model (always) and reranker model (if available) on startup."""
    global embed_tokenizer, embed_model, device
    global reranker_tokenizer, reranker_model
    global reranker_yes_token_id, reranker_no_token_id, reranker_available

    device = _resolve_device(DEVICE)

    # ── Embedding model (always loaded) ──────────────────────────────────
    logger.info("Loading embedding tokenizer from %s", MODEL_PATH)
    embed_tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)

    if POOLING_STRATEGY == "last_token":
        embed_tokenizer.padding_side = "left"
        logger.info("Configured left-padding for last-token pooling")

    logger.info("Loading embedding model from %s", MODEL_PATH)
    embed_model = AutoModel.from_pretrained(MODEL_PATH)
    embed_model.to(device)
    embed_model.eval()

    logger.info(
        "Embedding model loaded — device=%s, dim=%d, pooling=%s, max_length=%d",
        device, embed_model.config.hidden_size, POOLING_STRATEGY, MAX_LENGTH,
    )

    # ── Reranker model (optional) ────────────────────────────────────────
    if os.path.isdir(RERANKER_MODEL_PATH) and os.path.isfile(
        os.path.join(RERANKER_MODEL_PATH, "config.json"),
    ):
        logger.info("Loading reranker tokenizer from %s", RERANKER_MODEL_PATH)
        reranker_tokenizer = AutoTokenizer.from_pretrained(
            RERANKER_MODEL_PATH, padding_side="left",
        )

        logger.info("Loading reranker model from %s", RERANKER_MODEL_PATH)
        reranker_model = AutoModelForCausalLM.from_pretrained(
            RERANKER_MODEL_PATH, dtype=torch.float16,
        )
        reranker_model.to(device)
        reranker_model.eval()

        reranker_yes_token_id = reranker_tokenizer.convert_tokens_to_ids("yes")
        reranker_no_token_id = reranker_tokenizer.convert_tokens_to_ids("no")
        reranker_available = True

        logger.info(
            "Reranker model loaded — yes_id=%d, no_id=%d, params=%dM",
            reranker_yes_token_id, reranker_no_token_id,
            sum(p.numel() for p in reranker_model.parameters()) // 1_000_000,
        )
    else:
        logger.info(
            "Reranker model not found at %s — /rerank endpoint disabled",
            RERANKER_MODEL_PATH,
        )

    yield

    # Cleanup
    del embed_model, embed_tokenizer
    if reranker_model is not None:
        del reranker_model, reranker_tokenizer
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


# ── FastAPI app ──────────────────────────────────────────────────────────────

app = FastAPI(title="Embedding & Reranker Service", lifespan=lifespan)


# ── POST /embed ──────────────────────────────────────────────────────────────

class EmbedRequest(BaseModel):
    texts: list[str]


class EmbedResponse(BaseModel):
    embeddings: list[list[float]]


@app.post("/embed", response_model=EmbedResponse, )
async def embed(request: EmbedRequest):
    """Generate embeddings for a batch of texts."""
    if not request.texts:
        raise HTTPException(status_code=400, detail="texts must be a non-empty list")

    pool_fn = _POOLING_FN.get(POOLING_STRATEGY)
    if pool_fn is None:
        raise HTTPException(
            status_code=500,
            detail=f"Unknown pooling strategy: {POOLING_STRATEGY}",
        )

    try:
        encoded = embed_tokenizer(
            request.texts,
            padding=True,
            truncation=True,
            max_length=MAX_LENGTH,
            return_tensors="pt",
        )
        encoded = {k: v.to(device) for k, v in encoded.items()}

        with torch.no_grad():
            output = embed_model(**encoded)

        embeddings = pool_fn(output, encoded["attention_mask"])
        embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)
        result = embeddings.cpu().float().numpy().tolist()

        return EmbedResponse(embeddings=result)

    except Exception as e:
        logger.exception("Embedding failed")
        raise HTTPException(status_code=500, detail=str(e))


# ── POST /rerank ─────────────────────────────────────────────────────────────

class RerankRequest(BaseModel):
    query: str
    documents: list[str]
    instruction: str = "Given a web search query, retrieve relevant documents."
    top_n: int | None = None


class RerankResult(BaseModel):
    index: int
    score: float


class RerankResponse(BaseModel):
    results: list[RerankResult]


@app.post("/rerank", response_model=RerankResponse, )
async def rerank(request: RerankRequest):
    """Rerank documents by relevance to a query using cross-encoder scoring."""
    if not reranker_available:
        raise HTTPException(
            status_code=503,
            detail="Reranker model not loaded. Mount model at RERANKER_MODEL_PATH.",
        )

    if not request.documents:
        raise HTTPException(status_code=400, detail="documents must be a non-empty list")

    try:
        pairs = [
            _format_rerank_pair(request.query, doc, request.instruction)
            for doc in request.documents
        ]

        scores = _score_pairs(pairs)

        results = [
            RerankResult(index=i, score=s)
            for i, s in enumerate(scores)
        ]
        results.sort(key=lambda r: r.score, reverse=True)

        if request.top_n is not None:
            results = results[: request.top_n]

        logger.info(
            "Reranked %d documents for query '%s' — top: %.4f, min: %.4f",
            len(request.documents), request.query[:60],
            results[0].score if results else 0.0,
            results[-1].score if results else 0.0,
        )

        return RerankResponse(results=results)

    except Exception as e:
        logger.exception("Reranking failed")
        raise HTTPException(status_code=500, detail=str(e))


# ── GET /health ──────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "model_path": MODEL_PATH,
        "device": str(device),
        "embedding_dim": embed_model.config.hidden_size if embed_model else None,
        "pooling_strategy": POOLING_STRATEGY,
        "max_length": MAX_LENGTH,
        "reranker_available": reranker_available,
        "reranker_model_path": RERANKER_MODEL_PATH if reranker_available else None,
    }
