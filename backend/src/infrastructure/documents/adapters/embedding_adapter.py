from __future__ import annotations

import logging

import httpx

from src.config import settings
from src.domain.documents.ports.embedding_port import EmbeddingPort
from src.infrastructure.shared.auth.token_provider import TokenProvider

logger = logging.getLogger("iaph.embedding")


class HttpEmbeddingAdapter(EmbeddingPort):
    """HTTP client adapter for the MrBERT embedding service."""

    def __init__(self, token_provider: TokenProvider | None = None) -> None:
        self._base_url = settings.embedding_service_url
        self._token_provider = token_provider
        self._client = httpx.AsyncClient(timeout=120.0)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        preview = texts[0][:120] if texts else ""
        logger.info(
            "Embed request (documents): %d texts, total_chars=%d, preview=%r",
            len(texts), sum(len(t) for t in texts), preview,
        )
        headers = {}
        if self._token_provider:
            token = await self._token_provider.get_token()
            if token:
                headers["Authorization"] = f"Bearer {token}"
        response = await self._client.post(
            f"{self._base_url}/embed",
            json={"texts": texts},
            headers=headers,
        )
        response.raise_for_status()
        data = response.json()
        embeddings = data["embeddings"]
        logger.info(
            "Embed response (documents): %d embeddings, dim=%d",
            len(embeddings), len(embeddings[0]) if embeddings else 0,
        )
        return embeddings
