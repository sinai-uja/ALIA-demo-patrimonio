"""
Embedding service for MrBERT (BSC-LT/MrBERT).

Loads the model from a volume-mounted path and serves embeddings via HTTP.
Uses mean pooling over all token embeddings (NOT CLS token) as specified
by the model's classifier_pooling: "mean" configuration.
"""

import logging
import os
from contextlib import asynccontextmanager

import numpy as np
import torch
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from transformers import AutoModel, AutoTokenizer

logger = logging.getLogger("embedding-service")
logging.basicConfig(level=logging.INFO)

MODEL_PATH = os.environ.get("MODEL_PATH", "/app/model")
DEVICE = os.environ.get("DEVICE", "cpu")

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
    This is the correct pooling strategy for MrBERT (classifier_pooling: "mean").
    """
    token_embeddings = model_output[0]  # (batch, seq_len, hidden_dim)
    mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    sum_embeddings = torch.sum(token_embeddings * mask_expanded, dim=1)
    sum_mask = torch.clamp(mask_expanded.sum(dim=1), min=1e-9)
    return sum_embeddings / sum_mask


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load model and tokenizer on startup."""
    global tokenizer, model, device

    logger.info("Loading tokenizer from %s", MODEL_PATH)
    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)

    logger.info("Loading model from %s", MODEL_PATH)
    device = _resolve_device(DEVICE)
    model = AutoModel.from_pretrained(MODEL_PATH)
    model.to(device)
    model.eval()

    logger.info(
        "Model loaded — device=%s, embedding_dim=%d",
        device,
        model.config.hidden_size,
    )
    yield

    # Cleanup
    del model, tokenizer
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


app = FastAPI(title="MrBERT Embedding Service", lifespan=lifespan)


class EmbedRequest(BaseModel):
    texts: list[str]


class EmbedResponse(BaseModel):
    embeddings: list[list[float]]


@app.post("/embed", response_model=EmbedResponse)
async def embed(request: EmbedRequest):
    """Generate embeddings for a batch of texts using mean pooling."""
    if not request.texts:
        raise HTTPException(status_code=400, detail="texts must be a non-empty list")

    try:
        encoded = tokenizer(
            request.texts,
            padding=True,
            truncation=True,
            max_length=8192,
            return_tensors="pt",
        )
        encoded = {k: v.to(device) for k, v in encoded.items()}

        with torch.no_grad():
            output = model(**encoded)

        embeddings = mean_pooling(output, encoded["attention_mask"])
        embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)
        result = embeddings.cpu().numpy().tolist()

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
    }
