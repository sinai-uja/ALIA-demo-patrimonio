"""
Embedding service with dual encoder support (MrBERT / Qwen3-Embedding-0.6B).

Loads a transformer model from a volume-mounted path and serves embeddings via HTTP.
Pooling strategy is configurable via POOLING_STRATEGY env var:
  - "mean"       : Mean pooling over all token embeddings (MrBERT default)
  - "last_token" : Last-token pooling with left-padding (Qwen3 default)
"""

import logging
import os
from contextlib import asynccontextmanager

import torch
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from transformers import AutoModel, AutoTokenizer

logger = logging.getLogger("embedding-service")
logging.basicConfig(level=logging.INFO)

MODEL_PATH = os.environ.get("MODEL_PATH", "/app/model")
DEVICE = os.environ.get("DEVICE", "cpu")
POOLING_STRATEGY = os.environ.get("POOLING_STRATEGY", "mean")
MAX_LENGTH = int(os.environ.get("MAX_LENGTH", "8192"))

# Global references set during startup
tokenizer = None
model = None
device = None


def _resolve_device(requested: str) -> torch.device:
    """Resolve the compute device, falling back to CPU if CUDA is unavailable."""
    if requested == "cuda" and torch.cuda.is_available():
        logger.info("CUDA is available — using GPU")
        return torch.device("cuda")
    if requested == "cuda":
        logger.warning("CUDA requested but not available — falling back to CPU")
    return torch.device("cpu")


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
    seq_lengths = attention_mask.sum(dim=1)  # (batch,)
    batch_size = token_embeddings.shape[0]
    # The last non-padding token index = total_length - 1 (always rightmost with left-padding)
    last_indices = seq_lengths - 1  # noqa: F841
    # With left-padding the last token is always the rightmost, so just take [:, -1, :]
    return token_embeddings[:, -1, :]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load model and tokenizer on startup."""
    global tokenizer, model, device

    logger.info("Loading tokenizer from %s", MODEL_PATH)
    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)

    # Configure padding side based on pooling strategy
    if POOLING_STRATEGY == "last_token":
        tokenizer.padding_side = "left"
        logger.info("Configured left-padding for last-token pooling")

    logger.info("Loading model from %s", MODEL_PATH)
    device = _resolve_device(DEVICE)
    model = AutoModel.from_pretrained(MODEL_PATH)
    model.to(device)
    model.eval()

    logger.info(
        "Model loaded — device=%s, embedding_dim=%d, pooling=%s, max_length=%d",
        device,
        model.config.hidden_size,
        POOLING_STRATEGY,
        MAX_LENGTH,
    )
    yield

    # Cleanup
    del model, tokenizer
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


app = FastAPI(title="Embedding Service", lifespan=lifespan)


class EmbedRequest(BaseModel):
    texts: list[str]


class EmbedResponse(BaseModel):
    embeddings: list[list[float]]


_POOLING_FN = {
    "mean": mean_pooling,
    "last_token": last_token_pooling,
}


@app.post("/embed", response_model=EmbedResponse)
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
        encoded = tokenizer(
            request.texts,
            padding=True,
            truncation=True,
            max_length=MAX_LENGTH,
            return_tensors="pt",
        )
        encoded = {k: v.to(device) for k, v in encoded.items()}

        with torch.no_grad():
            output = model(**encoded)

        embeddings = pool_fn(output, encoded["attention_mask"])
        embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)
        result = embeddings.cpu().float().numpy().tolist()

        return EmbedResponse(embeddings=result)

    except Exception as e:
        logger.exception("Embedding failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "model_path": MODEL_PATH,
        "device": str(device),
        "embedding_dim": model.config.hidden_size if model else None,
        "pooling_strategy": POOLING_STRATEGY,
        "max_length": MAX_LENGTH,
    }
