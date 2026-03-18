from abc import ABC, abstractmethod

from src.domain.rag.entities.retrieved_chunk import RetrievedChunk


class VectorSearchPort(ABC):
    """Port for vector similarity search against stored document chunks."""

    @abstractmethod
    async def search(
        self,
        query_embedding: list[float],
        top_k: int,
        heritage_type: str | list[str] | None = None,
        province: str | list[str] | None = None,
        municipality: str | list[str] | None = None,
    ) -> list[RetrievedChunk]:
        ...
