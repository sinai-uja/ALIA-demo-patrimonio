"""CLI script for bulk ingestion of IAPH parquet datasets."""

import argparse
import asyncio
import logging
import sys
import time

from src.application.documents.dto.ingest_dto import IngestDocumentsCommand
from src.composition.documents_composition import build_documents_application_service
from src.db.base import AsyncSessionLocal

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

DATASETS = {
    "paisaje_cultural": (
        "../data/Guia_Digital_Patrimonio_Andalucia_Paisaje_Cultural.parquet",
        "paisaje_cultural",
    ),
    "patrimonio_inmaterial": (
        "../data/Guia_Digital_Patrimonio_Andalucia_Patrimonio_Inmaterial.parquet",
        "patrimonio_inmaterial",
    ),
    "patrimonio_inmueble": (
        "../data/Guia_Digital_Patrimonio_Andalucia_Patrimonio_Inmueble.parquet",
        "patrimonio_inmueble",
    ),
    "patrimonio_mueble": (
        "../data/Guia_Digital_Patrimonio_Andalucia_Patrimonio_Mueble.parquet",
        "patrimonio_mueble",
    ),
}


async def ingest_dataset(name: str, source_path: str, heritage_type: str) -> None:
    logger.info("Starting ingestion of '%s' from %s", name, source_path)
    start = time.time()

    async with AsyncSessionLocal() as db:
        service = build_documents_application_service(db)
        command = IngestDocumentsCommand(
            source_path=source_path,
            heritage_type=heritage_type,
            chunk_size=512,
            chunk_overlap=64,
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


async def main(datasets: dict[str, tuple[str, str]]) -> None:
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
    args = parser.parse_args()

    targets = DATASETS if args.dataset == "all" else {args.dataset: DATASETS[args.dataset]}
    asyncio.run(main(targets))


if __name__ == "__main__":
    cli()
