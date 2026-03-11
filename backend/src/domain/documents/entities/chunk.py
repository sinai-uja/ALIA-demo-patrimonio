from dataclasses import dataclass
from uuid import UUID


@dataclass
class Chunk:
    """A text chunk derived from a document."""

    id: UUID
    document_id: str
    content: str
    chunk_index: int
    token_count: int
