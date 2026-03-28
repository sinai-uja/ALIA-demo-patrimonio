from abc import ABC, abstractmethod

from src.domain.rag.entities.retrieved_chunk import RetrievedChunk


class RerankerPort(ABC):
    """Port for neural cross-encoder reranking."""

    @abstractmethod
    async def rerank(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        instruction: str = "",
        top_n: int | None = None,
    ) -> list[RetrievedChunk]:
        """Rerank chunks by cross-encoder relevance.

        Returns chunks sorted by relevance (most relevant first) with updated scores.
        Scores are relevance probabilities in [0, 1] where higher = more relevant.
        """
