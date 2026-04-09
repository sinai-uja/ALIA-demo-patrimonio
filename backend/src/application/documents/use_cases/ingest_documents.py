import logging
from dataclasses import replace

from src.application.documents.dto.ingest_dto import IngestDocumentsCommand, IngestResultDTO
from src.domain.documents.entities.chunk_embedding import ChunkEmbedding
from src.domain.documents.ports.document_loader import DocumentLoader
from src.domain.documents.ports.document_repository import DocumentRepository
from src.domain.documents.ports.embedding_port import EmbeddingPort
from src.domain.documents.services.chunking_service import ChunkingService
from src.domain.documents.services.document_enrichment_service import (
    DocumentEnrichmentService,
)
from src.domain.documents.value_objects.heritage_type import HeritageType
from src.domain.shared.ports.unit_of_work import UnitOfWork

logger = logging.getLogger("iaph")

EMBEDDING_BATCH_SIZE = 2


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
        enrichment_service: DocumentEnrichmentService,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._loader = document_loader
        self._chunker = chunking_service
        self._embedding_port = embedding_port
        self._repository = document_repository
        self._enrichment_service = enrichment_service
        self._uow = unit_of_work

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

            async with self._uow:
                # Embed and persist in batches. The enriched text is what
                # gets embedded AND what gets persisted as chunk.content so
                # that retrieval returns the same text that was vectorized.
                for batch_start in range(0, len(new_chunks), EMBEDDING_BATCH_SIZE):
                    batch = new_chunks[batch_start : batch_start + EMBEDDING_BATCH_SIZE]

                    enriched_batch = [
                        replace(
                            chunk,
                            content=self._enrichment_service.enrich(document, chunk).text,
                        )
                        for chunk in batch
                    ]
                    enriched_texts = [c.content for c in enriched_batch]

                    embeddings = await self._embedding_port.embed(enriched_texts)

                    for enriched_chunk, embedding_vector in zip(enriched_batch, embeddings):
                        embedding = ChunkEmbedding(
                            chunk_id=enriched_chunk.id,
                            embedding=embedding_vector,
                        )
                        await self._repository.save_chunk_with_embedding(
                            document, enriched_chunk, embedding
                        )

                total_chunks += len(new_chunks)

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
