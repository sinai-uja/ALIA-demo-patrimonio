from dataclasses import dataclass


@dataclass(frozen=True)
class RAGQuery:
    """Represents a user query with optional filters for the RAG pipeline."""

    query: str
    top_k: int = 5
    heritage_type_filter: str | None = None
    province_filter: str | None = None
