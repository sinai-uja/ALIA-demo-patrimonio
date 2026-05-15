import logging
from dataclasses import replace

from src.application.documents.dto.ingest_dto import IngestDocumentsCommand, IngestResultDTO
from src.domain.documents.entities.chunk_embedding import ChunkEmbedding
from src.domain.documents.ports.document_loader import DocumentLoader
from src.domain.documents.ports.document_repository import DocumentRepository
from src.domain.documents.services.chunking_service import ChunkingService
from src.domain.documents.services.document_enrichment_service import (
    DocumentEnrichmentService,
)
from src.domain.documents.value_objects.heritage_type import HeritageType
from src.domain.shared.ports.embedding_port import EmbeddingPort
from src.domain.shared.ports.unit_of_work import UnitOfWork

logger = logging.getLogger("iaph.documents.ingest")

EMBEDDING_BATCH_SIZE = 32


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

        # Pre-load every (document_id, chunk_index) pair already stored.
        # O(N) at start, O(1) per chunk afterwards — avoids 1 DB roundtrip
        # per chunk while remaining idempotent. ~50 bytes/row × 130K rows
        # = ~7 MB RAM, negligible.
        existing_keys = await self._repository.existing_chunk_keys()
        if existing_keys:
            logger.info(
                "Loaded %d existing chunk keys for idempotency check",
                len(existing_keys),
            )

        # Cross-document buffer: keeps (document, enriched_chunk) pairs that
        # still need an embedding. Flushed in batches of EMBEDDING_BATCH_SIZE
        # to amortise embedding-service latency across many documents.
        buffer: list[tuple] = []

        async def flush() -> int:
            """Embed every chunk in the buffer in a single request and persist."""
            if not buffer:
                return 0
            enriched_texts = [pair[1].content for pair in buffer]
            embeddings = await self._embedding_port.embed(enriched_texts)
            items = [
                (
                    doc,
                    enriched_chunk,
                    ChunkEmbedding(
                        chunk_id=enriched_chunk.id,
                        embedding=embedding_vector,
                    ),
                )
                for (doc, enriched_chunk), embedding_vector in zip(buffer, embeddings)
            ]
            async with self._uow:
                await self._repository.save_chunks_batch(items)
            persisted = len(items)
            buffer.clear()
            return persisted

        for document in self._loader.load_documents(command.source_path, heritage_type):
            total_documents += 1
            chunks = self._chunker.chunk_document(document)

            # Filter out already-existing chunks (idempotent ingestion) and
            # enrich the survivors before buffering them. Uses the in-memory
            # set pre-loaded above instead of a DB roundtrip per chunk.
            for chunk in chunks:
                key = (chunk.document_id, chunk.chunk_index)
                if key in existing_keys:
                    skipped_chunks += 1
                    continue
                existing_keys.add(key)  # avoid duplicates within the same run
                enriched_chunk = replace(
                    chunk,
                    content=self._enrichment_service.enrich(document, chunk).text,
                )
                buffer.append((document, enriched_chunk))

                if len(buffer) >= EMBEDDING_BATCH_SIZE:
                    total_chunks += await flush()

            if total_documents % 200 == 0:
                logger.info(
                    "Ingestion progress: %d documents processed, %d chunks created",
                    total_documents,
                    total_chunks,
                )

        # Flush any leftovers at the end.
        total_chunks += await flush()

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
