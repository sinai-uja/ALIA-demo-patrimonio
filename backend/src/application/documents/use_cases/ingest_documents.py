import logging

from src.application.documents.dto.ingest_dto import IngestDocumentsCommand, IngestResultDTO
from src.domain.documents.entities.chunk_embedding import ChunkEmbedding
from src.domain.documents.ports.document_loader import DocumentLoader
from src.domain.documents.ports.document_repository import DocumentRepository
from src.domain.documents.ports.embedding_port import EmbeddingPort
from src.domain.documents.services.chunking_service import ChunkingService
from src.domain.documents.value_objects.heritage_type import HeritageType

logger = logging.getLogger(__name__)

EMBEDDING_BATCH_SIZE = 8


class IngestDocumentsUseCase:
    """Orchestrates the full document ingestion pipeline:
    load -> chunk -> skip duplicates -> embed -> persist.
    """

    def __init__(
        self,
        document_loader: DocumentLoader,
        chunking_service: ChunkingService,
        embedding_port: EmbeddingPort,
        document_repository: DocumentRepository,
    ) -> None:
        self._loader = document_loader
        self._chunker = chunking_service
        self._embedding_port = embedding_port
        self._repository = document_repository

    async def execute(self, command: IngestDocumentsCommand) -> IngestResultDTO:
        heritage_type = HeritageType(command.heritage_type)

        # Reconfigure chunker with command parameters
        self._chunker.chunk_size = command.chunk_size
        self._chunker.chunk_overlap = command.chunk_overlap

        total_documents = 0
        total_chunks = 0
        skipped_chunks = 0

        for document in self._loader.load_documents(command.source_path, heritage_type):
            total_documents += 1
            chunks = self._chunker.chunk_document(document)

            # Filter out already-existing chunks (idempotent ingestion)
            new_chunks = []
            for chunk in chunks:
                exists = await self._repository.chunk_exists(
                    chunk.document_id, chunk.chunk_index
                )
                if exists:
                    skipped_chunks += 1
                else:
                    new_chunks.append(chunk)

            # Embed and persist in batches
            # Prepend metadata to each chunk for richer embeddings
            for batch_start in range(0, len(new_chunks), EMBEDDING_BATCH_SIZE):
                batch = new_chunks[batch_start : batch_start + EMBEDDING_BATCH_SIZE]
                texts = [
                    self._enrich_for_embedding(document, c.content) for c in batch
                ]
                embeddings = await self._embedding_port.embed(texts)

                for chunk, embedding_vector in zip(batch, embeddings):
                    embedding = ChunkEmbedding(
                        chunk_id=chunk.id,
                        embedding=embedding_vector,
                    )
                    await self._repository.save_chunk_with_embedding(
                        document, chunk, embedding
                    )

            total_chunks += len(new_chunks)
            await self._repository.commit()

            if total_documents % 50 == 0:
                logger.info(
                    "Ingestion progress: %d documents processed, %d chunks created",
                    total_documents,
                    total_chunks,
                )

        logger.info(
            "Ingestion complete: %d documents, %d new chunks, %d skipped",
            total_documents,
            total_chunks,
            skipped_chunks,
        )

        return IngestResultDTO(
            total_documents=total_documents,
            total_chunks=total_chunks,
            skipped_chunks=skipped_chunks,
        )

    @staticmethod
    def _enrich_for_embedding(document, content: str) -> str:
        """Prepend document metadata to chunk content for richer embeddings.

        The embedding model encodes title, heritage type, and location alongside
        the chunk text, improving retrieval for queries by name or place.
        """
        parts = [f"Titulo: {document.title}"]
        parts.append(f"Tipo: {document.heritage_type.value}")
        parts.append(f"Provincia: {document.province}")
        if document.municipality:
            parts.append(f"Municipio: {document.municipality}")
        header = " | ".join(parts)
        return f"{header}\n---\n{content}"
