from dataclasses import dataclass
from uuid import UUID


@dataclass
class ChunkEmbedding:
    """Embedding vector associated with a chunk."""

    chunk_id: UUID
    embedding: list[float]
