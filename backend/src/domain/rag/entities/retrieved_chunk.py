from dataclasses import dataclass


@dataclass(frozen=True)
class RetrievedChunk:
    """A document chunk retrieved from vector search with its relevance score."""

    chunk_id: str
    document_id: str
    title: str
    heritage_type: str
    province: str
    municipality: str | None
    url: str
    content: str
    score: float
