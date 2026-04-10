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
    async def get_chunks_by_document(self, document_id: str) -> list[Chunk]: ...

    @abstractmethod
    async def chunk_exists(self, document_id: str, chunk_index: int) -> bool: ...

    @abstractmethod
    async def delete_all_chunks(self) -> int: ...
