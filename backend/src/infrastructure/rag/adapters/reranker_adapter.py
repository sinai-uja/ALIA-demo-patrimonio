from __future__ import annotations

import logging
from dataclasses import replace

import httpx

from src.config import settings
from src.domain.rag.entities.retrieved_chunk import RetrievedChunk
from src.domain.rag.ports.reranker_port import RerankerPort
from src.infrastructure.shared.auth.token_provider import TokenProvider

logger = logging.getLogger("iaph.reranker")


class HttpRerankerAdapter(RerankerPort):
    """Calls the reranker microservice via HTTP to score query-document pairs."""

    def __init__(
        self,
        base_url: str | None = None,
        token_provider: TokenProvider | None = None,
    ) -> None:
        self._base_url = base_url or settings.reranker_service_url
        self._token_provider = token_provider

    async def rerank(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        instruction: str = "",
        top_n: int | None = None,
    ) -> list[RetrievedChunk]:
        if not chunks:
            return []

        documents = [chunk.content for chunk in chunks]
        headers = {}
        if self._token_provider:
            token = await self._token_provider.get_token()
            if token:
                headers["Authorization"] = f"Bearer {token}"

        payload = {
            "query": query,
            "documents": documents,
            "instruction": instruction,
        }
        if top_n is not None:
            payload["top_n"] = top_n

        logger.info(
            "Rerank request: %d documents, query='%s'",
            len(documents), query[:60],
        )

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self._base_url}/rerank",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()

        results = data["results"]
        logger.info("Rerank response: %d results", len(results))

        # Map scores back to chunks, converting from relevance (higher=better)
        # to distance-like scale (lower=better) for pipeline compatibility
        reranked = []
        for result in results:
            idx = result["index"]
            relevance = result["score"]
            distance_score = 1.0 - relevance  # 0 = most relevant
            reranked.append(replace(chunks[idx], score=distance_score))

        return reranked
