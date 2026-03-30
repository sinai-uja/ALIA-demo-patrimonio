from __future__ import annotations

import logging

import httpx

from src.config import settings
from src.domain.rag.ports.embedding_port import EmbeddingPort
from src.infrastructure.shared.auth.token_provider import TokenProvider

logger = logging.getLogger("iaph.embedding")


class HttpEmbeddingAdapter(EmbeddingPort):
    """Calls the internal embedding service via HTTP to generate embeddings."""

    def __init__(
        self,
        base_url: str | None = None,
        token_provider: TokenProvider | None = None,
    ) -> None:
        self._base_url = base_url or settings.embedding_service_url
        self._token_provider = token_provider

    async def embed(self, texts: list[str]) -> list[list[float]]:
        preview = texts[0][:120] if texts else ""
        logger.info(
            "Embed request (rag): %d texts, total_chars=%d, preview=%r",
            len(texts), sum(len(t) for t in texts), preview,
        )
        headers = {}
        if self._token_provider:
            token = await self._token_provider.get_token()
            if token:
                headers["Authorization"] = f"Bearer {token}"
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self._base_url}/embed",
                json={"texts": texts},
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()
            embeddings = data["embeddings"]
            logger.info(
                "Embed response (rag): %d embeddings, dim=%d",
                len(embeddings), len(embeddings[0]) if embeddings else 0,
            )
            return embeddings
