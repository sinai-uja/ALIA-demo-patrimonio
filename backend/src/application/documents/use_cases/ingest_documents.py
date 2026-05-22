import asyncio
import logging
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
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

EMBEDDING_BATCH_SIZE = 16
EMBEDDING_CONCURRENCY = 4  # how many batches in flight against the embedding service

# A batch context yields a (repository, unit_of_work) pair backed by a fresh
# DB session that the caller will use to persist a single embedding batch.
# Returning these as ports keeps the use case off any concrete SQLAlchemy
# import — the script/composition root provides the concrete plumbing.
BatchContext = Callable[
    [],
    "AsyncIterator[tuple[DocumentRepository, UnitOfWork]]",
]


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
        batch_context: BatchContext | None = None,
    ) -> None:
        self._loader = document_loader
        self._chunker = chunking_service
        self._embedding_port = embedding_port
        self._repository = document_repository
        self._enrichment_service = enrichment_service
        self._uow = unit_of_work
        # Optional. When provided, each concurrent embedding batch gets its
        # own (repo, uow) pair via this context manager. Required for
        # EMBEDDING_CONCURRENCY > 1 to avoid sharing a single DB session
        # across multiple in-flight INSERTs (asyncpg cannot interleave
        # transactions on one connection).
        self._batch_context = batch_context

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

        # Concurrency control: bound the number of batches in flight against
        # the embedding service so we don't drown Cloud Run, while still
        # overlapping network latency.
        semaphore = asyncio.Semaphore(EMBEDDING_CONCURRENCY)
        in_flight: set[asyncio.Task] = set()
        persisted_counter = {"value": 0}
        first_error: list[BaseException] = []

        # Sentinel: in single-session mode, every batch shares this UoW/repo.
        # In multi-session mode, each batch opens its own pair via the context.
        @asynccontextmanager
        async def _shared_pair() -> AsyncIterator[
            tuple[DocumentRepository, UnitOfWork],
        ]:
            yield self._repository, self._uow

        batch_ctx: Callable[
            [],
            AsyncIterator[tuple[DocumentRepository, UnitOfWork]],
        ] = self._batch_context if self._batch_context is not None else _shared_pair

        async def _process_batch(batch: list[tuple]) -> int:
            async with semaphore:
                enriched_texts = [pair[1].content for pair in batch]
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
                    for (doc, enriched_chunk), embedding_vector in zip(batch, embeddings)
                ]
                async with batch_ctx() as (repo, uow):
                    async with uow:
                        await repo.save_chunks_batch(items)
                return len(items)

        async def _track(task: asyncio.Task) -> None:
            try:
                # Sequence the await BEFORE the read-modify-write of the shared
                # counter — otherwise concurrent trackers would clobber each
                # other (Python `+=` is not atomic across an await).
                amount = await task
                persisted_counter["value"] += amount
            except BaseException as exc:  # noqa: BLE001
                if not first_error:
                    first_error.append(exc)
                logger.error("Batch failed: %s", exc, exc_info=True)

        def schedule_flush() -> None:
            if not buffer:
                return
            batch = list(buffer)
            buffer.clear()
            task = asyncio.create_task(_process_batch(batch))
            tracker = asyncio.create_task(_track(task))
            in_flight.add(tracker)
            tracker.add_done_callback(in_flight.discard)

        async def drain_one_if_full() -> None:
            """If we have more than EMBEDDING_CONCURRENCY*2 tasks queued,
            wait for one to finish so memory and the Cloud Run queue stay bounded."""
            while len(in_flight) >= EMBEDDING_CONCURRENCY * 2:
                done, _pending = await asyncio.wait(
                    in_flight, return_when=asyncio.FIRST_COMPLETED,
                )
                # callbacks above already removed them from in_flight
                # but await is needed to surface exceptions
                for t in done:
                    await t

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
                    schedule_flush()
                    await drain_one_if_full()

            if total_documents % 200 == 0:
                logger.info(
                    "Ingestion progress: %d documents processed, %d chunks persisted",
                    total_documents,
                    persisted_counter["value"],
                )

        # Flush any leftovers at the end.
        schedule_flush()
        # Wait for every in-flight task to finish.
        if in_flight:
            await asyncio.gather(*in_flight, return_exceptions=False)

        if first_error:
            raise first_error[0]

        total_chunks = persisted_counter["value"]

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
