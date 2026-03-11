from dataclasses import dataclass

from src.domain.rag.entities.retrieved_chunk import RetrievedChunk


@dataclass(frozen=True)
class RAGResponse:
    """The complete response from the RAG pipeline."""

    answer: str
    retrieved_chunks: list[RetrievedChunk]
    query: str
