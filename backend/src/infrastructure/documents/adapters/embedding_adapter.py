import logging

import httpx

from src.config import settings
from src.domain.documents.ports.embedding_port import EmbeddingPort

logger = logging.getLogger("iaph.embedding")


class HttpEmbeddingAdapter(EmbeddingPort):
    """HTTP client adapter for the MrBERT embedding service."""

    def __init__(self) -> None:
        self._base_url = settings.embedding_service_url

    async def embed(self, texts: list[str]) -> list[list[float]]:
        preview = texts[0][:120] if texts else ""
        logger.info(
            "Embed request (documents): %d texts, total_chars=%d, preview=%r",
            len(texts), sum(len(t) for t in texts), preview,
        )
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self._base_url}/embed",
                json={"texts": texts},
            )
            response.raise_for_status()
            data = response.json()
            embeddings = data["embeddings"]
            logger.info(
                "Embed response (documents): %d embeddings, dim=%d",
                len(embeddings), len(embeddings[0]) if embeddings else 0,
            )
            return embeddings
