from dataclasses import dataclass


@dataclass(frozen=True)
class SimplifyTextDTO:
    """Input DTO for a text simplification request."""

    text: str
    level: str = "basic"
    document_id: str | None = None


@dataclass(frozen=True)
class SimplifiedTextDTO:
    """Output DTO for a text simplification response."""

    original_text: str
    simplified_text: str
    level: str
    document_id: str | None
    created_at: str


@dataclass(frozen=True)
class SimplifyChunksDTO:
    """Input DTO for simplifying all chunks of a document from the RAG store."""

    document_id: str
    level: str = "basic"
