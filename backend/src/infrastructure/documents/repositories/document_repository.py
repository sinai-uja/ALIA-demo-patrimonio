from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.documents.entities.chunk import Chunk
from src.domain.documents.entities.chunk_embedding import ChunkEmbedding
from src.domain.documents.entities.document import Document
from src.domain.documents.ports.document_repository import (
    DocumentRepository as DocumentRepositoryPort,
)
from src.infrastructure.documents.models import DocumentChunkModel


class SqlAlchemyDocumentRepository(DocumentRepositoryPort):
    """Async SQLAlchemy implementation of the DocumentRepository port."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save_chunk_with_embedding(
        self, document: Document, chunk: Chunk, embedding: ChunkEmbedding
    ) -> None:
        model = DocumentChunkModel(
            id=chunk.id,
            document_id=chunk.document_id,
            heritage_type=document.heritage_type.value,
            title=document.title,
            province=document.province,
            municipality=document.municipality,
            url=document.url,
            chunk_index=chunk.chunk_index,
            content=chunk.content,
            token_count=chunk.token_count,
            embedding=embedding.embedding,
        )
        self._session.add(model)
        await self._session.flush()

    async def get_chunks_by_document(self, document_id: str) -> list[Chunk]:
        stmt = (
            select(DocumentChunkModel)
            .where(DocumentChunkModel.document_id == document_id)
            .order_by(DocumentChunkModel.chunk_index)
        )
        result = await self._session.execute(stmt)
        rows = result.scalars().all()
        return [
            Chunk(
                id=row.id,
                document_id=row.document_id,
                content=row.content,
                chunk_index=row.chunk_index,
                token_count=row.token_count,
            )
            for row in rows
        ]

    async def chunk_exists(self, document_id: str, chunk_index: int) -> bool:
        stmt = select(DocumentChunkModel.id).where(
            DocumentChunkModel.document_id == document_id,
            DocumentChunkModel.chunk_index == chunk_index,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None
