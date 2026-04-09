from __future__ import annotations

import asyncio
import logging

import httpx

from src.config import settings
from src.domain.documents.ports.embedding_port import EmbeddingPort
from src.infrastructure.shared.auth.token_provider import TokenProvider
from src.infrastructure.shared.exceptions import EmbeddingServiceUnavailableError

logger = logging.getLogger("iaph.embedding")


class HttpEmbeddingAdapter(EmbeddingPort):
    """HTTP client adapter for the MrBERT embedding service.

    Implements transparent retry/backoff for batch failures: if a batch
    request fails and the batch has more than one item, falls back to
    per-item requests after a short delay. When all retries are exhausted,
    raises `EmbeddingServiceUnavailableError`.
    """

    def __init__(self, token_provider: TokenProvider | None = None) -> None:
        self._base_url = settings.embedding_service_url
        self._token_provider = token_provider
        self._client = httpx.AsyncClient(timeout=120.0)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return await self._embed_with_retry(texts)

    async def _embed_with_retry(self, texts: list[str]) -> list[list[float]]:
        """Embed texts with fallback to one-by-one on failures."""
        try:
            return await self._embed_raw(texts)
        except EmbeddingServiceUnavailableError:
            if len(texts) <= 1:
                raise
            logger.warning(
                "Embedding batch of %d failed, retrying one-by-one", len(texts)
            )
            await asyncio.sleep(2)
            results: list[list[float]] = []
            for t in texts:
                single = await self._embed_raw([t])
                results.append(single[0])
            return results

    async def _embed_raw(self, texts: list[str]) -> list[list[float]]:
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
        try:
            response = await self._client.post(
                f"{self._base_url}/embed",
                json={"texts": texts},
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPError as exc:
            raise EmbeddingServiceUnavailableError(
                f"Embedding service request failed: {exc}"
            ) from exc
        embeddings = data["embeddings"]
        logger.info(
            "Embed response (documents): %d embeddings, dim=%d",
            len(embeddings), len(embeddings[0]) if embeddings else 0,
        )
        return embeddings
