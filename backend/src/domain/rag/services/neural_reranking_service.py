import logging

from src.domain.rag.entities.retrieved_chunk import RetrievedChunk
from src.domain.rag.ports.reranker_port import RerankerPort

logger = logging.getLogger("iaph.rag.reranker")


class NeuralRerankingService:
    """Neural cross-encoder reranking service.

    Wraps a RerankerPort with pipeline logic: caps candidates, pre-sorts,
    converts scores to distance-like scale for downstream compatibility.
    """

    def __init__(
        self,
        reranker_port: RerankerPort,
        instruction: str = "Given a heritage search query, retrieve relevant heritage documents.",
        top_n: int = 50,
    ) -> None:
        self._reranker_port = reranker_port
        self._instruction = instruction
        self._top_n = top_n

    async def rerank(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        top_k: int,
    ) -> list[RetrievedChunk]:
        if not chunks:
            return []

        # Cap candidates to limit latency (pre-sort by existing score, lower = better)
        candidates = sorted(chunks, key=lambda c: c.score)[: self._top_n]
        logger.info(
            "Neural rerank: %d candidates (capped from %d) for query: %s",
            len(candidates), len(chunks), query[:80],
        )

        # Call the reranker service
        reranked = await self._reranker_port.rerank(
            query=query,
            chunks=candidates,
            instruction=self._instruction,
            top_n=top_k,
        )

        if not reranked:
            logger.info("Neural rerank returned no results")
            return []

        for i, chunk in enumerate(reranked[:top_k], 1):
            logger.info(
                "Neural reranked #%d: score=%.4f | title: %s | type: %s | province: %s",
                i, chunk.score, chunk.title[:60],
                chunk.heritage_type or "-", chunk.province or "-",
            )

        return reranked[:top_k]
