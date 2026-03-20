from dataclasses import dataclass, field


@dataclass(frozen=True)
class RAGQueryDTO:
    """Input DTO for a RAG query request."""

    query: str
    top_k: int = 5
    heritage_type_filter: str | None = None
    province_filter: str | None = None
    municipality_filter: str | None = None


@dataclass(frozen=True)
class SourceDTO:
    """A single source reference from the retrieved chunks."""

    title: str
    url: str
    score: float
    heritage_type: str
    province: str
    municipality: str | None = None
    document_id: str = ""
    content: str = ""
    metadata: dict | None = None


@dataclass(frozen=True)
class RAGResponseDTO:
    """Output DTO for a RAG query response."""

    answer: str
    sources: list[SourceDTO] = field(default_factory=list)
    query: str = ""
    abstained: bool = False
