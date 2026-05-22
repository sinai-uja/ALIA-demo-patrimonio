"""CLI script for bulk ingestion of IAPH parquet datasets."""

import argparse
import asyncio
import logging
import time

# Register related ORM models so SQLAlchemy can resolve the FK from
# document_chunks_v* to heritage_assets at mapper configuration time.
import src.infrastructure.heritage.models  # noqa: F401
from src.application.documents.dto.ingest_dto import IngestDocumentsCommand
from src.composition.documents_composition import build_documents_application_service
from src.config import settings
from src.infrastructure.documents.repositories.document_repository import (
    SqlAlchemyDocumentRepository,
)
from src.infrastructure.shared.adapters.sqlalchemy_unit_of_work import (
    SqlAlchemyUnitOfWork,
)
from src.infrastructure.shared.persistence.engine import AsyncSessionLocal

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

# Legacy parquet datasets (v1..v5).
_PARQUET_DATASETS: dict[str, tuple[str, str]] = {
    "paisaje_cultural": (
        "../data/Guia_Digital_Patrimonio_Andalucia/Guia_Digital_Patrimonio_Andalucia_Paisaje_Cultural.parquet",
        "paisaje_cultural",
    ),
    "patrimonio_inmaterial": (
        "../data/Guia_Digital_Patrimonio_Andalucia/Guia_Digital_Patrimonio_Andalucia_Patrimonio_Inmaterial.parquet",
        "patrimonio_inmaterial",
    ),
    "patrimonio_inmueble": (
        "../data/Guia_Digital_Patrimonio_Andalucia/Guia_Digital_Patrimonio_Andalucia_Patrimonio_Inmueble.parquet",
        "patrimonio_inmueble",
    ),
    "patrimonio_mueble": (
        "../data/Guia_Digital_Patrimonio_Andalucia/Guia_Digital_Patrimonio_Andalucia_Patrimonio_Mueble.parquet",
        "patrimonio_mueble",
    ),
}

# New JSONL datasets from Samuel (UJA) — used when chunks_table_version
# is ``v6``. Each file is a JSONL with one record per line.
_JSONL_DATASETS: dict[str, tuple[str, str]] = {
    "paisaje_cultural": (
        "../data/iaph_nuevo/paisaje.jsonl",
        "paisaje_cultural",
    ),
    "patrimonio_inmaterial": (
        "../data/iaph_nuevo/inmaterial.jsonl",
        "patrimonio_inmaterial",
    ),
    "patrimonio_inmueble": (
        "../data/iaph_nuevo/inmueble.jsonl",
        "patrimonio_inmueble",
    ),
    "patrimonio_mueble": (
        "../data/iaph_nuevo/mueble.jsonl",
        "patrimonio_mueble",
    ),
}


def _select_datasets() -> dict[str, tuple[str, str]]:
    """Pick dataset paths based on the active chunks_table_version."""
    if settings.chunks_table_version == "v6":
        return _JSONL_DATASETS
    return _PARQUET_DATASETS


DATASETS = _select_datasets()


async def purge_chunks() -> int:
    """Delete all chunks from the current chunks table."""
    async with AsyncSessionLocal() as db:
        repo = SqlAlchemyDocumentRepository(session=db)
        uow = SqlAlchemyUnitOfWork(session=db)
        async with uow:
            deleted = await repo.delete_all_chunks()
    return deleted


async def ingest_dataset(name: str, source_path: str, heritage_type: str) -> None:
    logger.info("Starting ingestion of '%s' from %s", name, source_path)
    start = time.time()

    # Build a batch_context that opens a *fresh* session per embedding batch.
    # This is what unlocks safe concurrency: each in-flight INSERT runs on a
    # separate asyncpg connection so they can't fight over a single
    # transaction. The main session below is still used by the use case for
    # the one-shot existing_chunk_keys() pre-load.
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def _batch_context():
        async with AsyncSessionLocal() as session:
            repo = SqlAlchemyDocumentRepository(session=session)
            uow = SqlAlchemyUnitOfWork(session=session)
            yield repo, uow

    async with AsyncSessionLocal() as db:
        service = build_documents_application_service(db, batch_context=_batch_context)
        command = IngestDocumentsCommand(
            source_path=source_path,
            heritage_type=heritage_type,
            chunk_size=settings.rag_chunk_size,
            chunk_overlap=settings.rag_chunk_overlap,
        )
        result = await service.ingest_documents(command)

    elapsed = time.time() - start
    logger.info(
        "Done '%s': %d documents, %d chunks created, %d skipped (%.1fs)",
        name,
        result.total_documents,
        result.total_chunks,
        result.skipped_chunks,
        elapsed,
    )


async def main(datasets: dict[str, tuple[str, str]], *, reingest: bool = False) -> None:
    if reingest:
        deleted = await purge_chunks()
        logger.info(
            "Reingest: deleted %d existing chunks from '%s'",
            deleted,
            settings.chunks_table_name,
        )

    for name, (path, ht) in datasets.items():
        await ingest_dataset(name, path, ht)


def cli() -> None:
    parser = argparse.ArgumentParser(description="Ingest IAPH parquet datasets into the database.")
    parser.add_argument(
        "--dataset",
        choices=[*DATASETS, "all"],
        default="all",
        help="Dataset to ingest (default: all)",
    )
    parser.add_argument(
        "--reingest",
        action="store_true",
        help="Delete all existing chunks before ingesting (full re-ingestion)",
    )
    args = parser.parse_args()

    targets = DATASETS if args.dataset == "all" else {args.dataset: DATASETS[args.dataset]}
    asyncio.run(main(targets, reingest=args.reingest))


if __name__ == "__main__":
    cli()
