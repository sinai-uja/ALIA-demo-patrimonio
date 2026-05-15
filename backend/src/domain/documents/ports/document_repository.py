from abc import ABC, abstractmethod

from src.domain.documents.entities.chunk import Chunk
from src.domain.documents.entities.chunk_embedding import ChunkEmbedding
from src.domain.documents.entities.document import Document


class DocumentRepository(ABC):
    """Port for persisting document chunks and their embeddings."""

    @abstractmethod
    async def save_chunk_with_embedding(
        self, document: Document, chunk: Chunk, embedding: ChunkEmbedding
    ) -> None: ...

    @abstractmethod
    async def save_chunks_batch(
        self,
        items: list[tuple[Document, Chunk, ChunkEmbedding]],
    ) -> None:
        """Persist a batch of chunks in a single transaction.

        Avoids the per-row flush() roundtrip used by save_chunk_with_embedding
        and is the recommended path for bulk ingestion.
        """
        ...

    @abstractmethod
    async def get_chunks_by_document(self, document_id: str) -> list[Chunk]: ...

    @abstractmethod
    async def chunk_exists(self, document_id: str, chunk_index: int) -> bool: ...

    @abstractmethod
    async def existing_chunk_keys(self) -> set[tuple[str, int]]:
        """Return the set of (document_id, chunk_index) pairs already stored.

        Loaded once at the start of an ingestion run so the use case can
        check existence in O(1) memory without a DB roundtrip per chunk.
        """
        ...

    @abstractmethod
    async def delete_all_chunks(self) -> int: ...
