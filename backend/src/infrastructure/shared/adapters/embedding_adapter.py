from __future__ import annotations

import asyncio
import logging

from src.config import settings
from src.domain.shared.ports.embedding_port import EmbeddingPort
from src.infrastructure.shared.auth.token_provider import TokenProvider
from src.application.shared.exceptions import (
    EmbeddingServiceUnavailableError,
)
from src.infrastructure.shared.http.httpx_client import post_json

logger = logging.getLogger("iaph.shared.embedding")


class HttpEmbeddingAdapter(EmbeddingPort):
    """HTTP client adapter for the embedding service.

    Uses the shared ``post_json`` httpx helper so all transport / status
    errors are translated into ``EmbeddingServiceUnavailableError``.

    Implements transparent retry/backoff for batch failures: if a batch
    request fails and the batch has more than one item, falls back to
    per-item requests after a short delay. When all retries are exhausted,
    the last ``EmbeddingServiceUnavailableError`` propagates.
    """

    def __init__(
        self,
        base_url: str | None = None,
        token_provider: TokenProvider | None = None,
    ) -> None:
        self._base_url = base_url or settings.embedding_service_url
        self._token_provider = token_provider

    async def embed(self, texts: list[str]) -> list[list[float]]:
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
            "Embed request: %d texts, total_chars=%d, preview=%r",
            len(texts), sum(len(t) for t in texts), preview,
        )
        headers: dict[str, str] = {}
        if self._token_provider:
            token = await self._token_provider.get_token()
            if token:
                headers["Authorization"] = f"Bearer {token}"
        data = await post_json(
            f"{self._base_url}/embed",
            {"texts": texts},
            service_label="embedding",
            timeout=120.0,
            headers=headers or None,
            error_class=EmbeddingServiceUnavailableError,
        )
        embeddings = data["embeddings"]
        logger.info(
            "Embed response: %d embeddings, dim=%d",
            len(embeddings), len(embeddings[0]) if embeddings else 0,
        )
        return embeddings
