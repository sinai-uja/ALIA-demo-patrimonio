"""Fetch heritage assets from the IAPH API and upsert into heritage_assets table.

Requires a Bearer token from the IAPH Guía Digital (see data/API_IAPH.zip README).

Usage:
    cd backend
    uv run python -m scripts.fetch_iaph_api --token "YOUR_BEARER_TOKEN"
    uv run python -m scripts.fetch_iaph_api --token "YOUR_BEARER_TOKEN" --dataset inmueble
    uv run python -m scripts.fetch_iaph_api --token "YOUR_BEARER_TOKEN" --page-size 500

Environment variable alternative:
    export IAPH_API_TOKEN="YOUR_BEARER_TOKEN"
    uv run python -m scripts.fetch_iaph_api
"""

import argparse
import asyncio
import json
import logging
import os
import time

import httpx
from sqlalchemy import text as sql_text
from src.db.base import AsyncSessionLocal

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

API_BASE = "https://guiadigital.iaph.es/api/1.0/busqueda"

DATASETS = {
    "inmueble": "inmueble",
    "mueble": "mueble",
    "inmaterial": "inmaterial",
    "paisaje": "paisaje",
}

# Reuse extraction logic from load_api_assets
from scripts.load_api_assets import _clean_raw_data, _extract_common_fields  # noqa: E402

UPSERT_SQL = sql_text("""
    INSERT INTO heritage_assets
        (id, heritage_type, denomination, province, municipality,
         latitude, longitude, image_url, image_ids, protection,
         raw_data, created_at, updated_at)
    VALUES
        (:id, :heritage_type, :denomination, :province, :municipality,
         :latitude, :longitude, :image_url, :image_ids, :protection,
         :raw_data, NOW(), NOW())
    ON CONFLICT (id) DO UPDATE SET
        heritage_type = EXCLUDED.heritage_type,
        denomination = EXCLUDED.denomination,
        province = EXCLUDED.province,
        municipality = EXCLUDED.municipality,
        latitude = EXCLUDED.latitude,
        longitude = EXCLUDED.longitude,
        image_url = EXCLUDED.image_url,
        image_ids = EXCLUDED.image_ids,
        protection = EXCLUDED.protection,
        raw_data = EXCLUDED.raw_data,
        updated_at = NOW()
""")


async def fetch_page(
    client: httpx.AsyncClient,
    heritage_type: str,
    start: int,
    rows: int,
    token: str,
) -> tuple[list[dict], int]:
    """Fetch a page of results from the IAPH API. Returns (docs, total_found)."""
    url = f"{API_BASE}/{heritage_type}/rows={rows}&start={start}&q=id:*"
    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {token}",
    }

    response = await client.get(url, headers=headers)
    response.raise_for_status()
    data = response.json()

    docs = data.get("response", {}).get("docs", [])
    num_found = data.get("response", {}).get("numFound", 0)
    return docs, num_found


async def fetch_and_upsert_dataset(
    token: str,
    heritage_type: str,
    page_size: int = 500,
    delay: float = 1.0,
    max_retries: int = 3,
) -> int:
    """Fetch all assets of a heritage type from the API and upsert them.

    Returns (total_upserted, token_expired).
    """
    logger.info(
        "Fetching %s from IAPH API (page_size=%d, delay=%.1fs)...",
        heritage_type, page_size, delay,
    )
    start_time = time.time()
    total_upserted = 0
    num_found = None

    # Resume: skip records already in DB for this heritage_type
    async with AsyncSessionLocal() as count_db:
        result = await count_db.execute(
            sql_text(
                "SELECT COUNT(*) FROM heritage_assets"
                " WHERE heritage_type = :ht"
            ),
            {"ht": heritage_type},
        )
        existing = result.scalar() or 0

    offset = existing
    if existing:
        logger.info(
            "  %s: %d assets already in DB, resuming from offset %d",
            heritage_type, existing, offset,
        )

    async with httpx.AsyncClient(timeout=60.0, verify=False) as client:
        async with AsyncSessionLocal() as db:
            while True:
                # Fetch with retries + exponential backoff
                docs = None
                for attempt in range(max_retries):
                    try:
                        docs, num_found_response = await fetch_page(
                            client, heritage_type, offset, page_size, token
                        )
                        if num_found is None:
                            num_found = num_found_response
                            logger.info(
                                "  %s: %d total assets reported by API",
                                heritage_type, num_found,
                            )
                        break
                    except httpx.HTTPStatusError as e:
                        if e.response.status_code == 401:
                            logger.error(
                                "  %s: token expired (401) at offset %d.",
                                heritage_type, offset,
                            )
                            if total_upserted:
                                await db.commit()
                            return total_upserted, True
                        wait = delay * (2**attempt)
                        logger.warning(
                            "  HTTP %d on attempt %d, retrying in %.1fs...",
                            e.response.status_code, attempt + 1, wait,
                        )
                        await asyncio.sleep(wait)
                    except httpx.RequestError as e:
                        wait = delay * (2**attempt)
                        logger.warning(
                            "  Request error on attempt %d: %s, retrying in %.1fs...",
                            attempt + 1, str(e)[:100], wait,
                        )
                        await asyncio.sleep(wait)

                if docs is None:
                    logger.error(
                        "  Failed to fetch page at offset %d after %d retries",
                        offset, max_retries,
                    )
                    break

                if not docs:
                    break

                # Upsert batch
                for doc in docs:
                    common = _extract_common_fields(doc, heritage_type)
                    common["raw_data"] = json.dumps(_clean_raw_data(doc))
                    await db.execute(UPSERT_SQL, common)

                total_upserted += len(docs)
                offset += page_size

                logger.info(
                    "  %s: %d / %s fetched",
                    heritage_type, total_upserted,
                    str(num_found) if num_found else "?",
                )

                await db.commit()

                # Rate limiting
                await asyncio.sleep(delay)

                # Safety: if we've fetched beyond num_found
                if num_found and offset >= num_found:
                    break

    elapsed = time.time() - start_time
    logger.info(
        "Done %s: %d assets fetched and upserted (%.1fs)",
        heritage_type, total_upserted, elapsed,
    )
    return total_upserted, False


async def main(token: str, datasets: list[str], page_size: int, delay: float) -> None:
    grand_total = 0
    for heritage_type in datasets:
        count, expired = await fetch_and_upsert_dataset(
            token, heritage_type, page_size, delay,
        )
        grand_total += count
        if expired:
            logger.warning(
                "Token expired during %s. Skipping remaining datasets.",
                heritage_type,
            )
            break
    logger.info("Grand total: %d assets fetched", grand_total)


def cli() -> None:
    parser = argparse.ArgumentParser(description="Fetch IAPH API data into heritage_assets table.")
    parser.add_argument(
        "--token",
        default=os.environ.get("IAPH_API_TOKEN"),
        help="Bearer token for IAPH API (or set IAPH_API_TOKEN env var)",
    )
    parser.add_argument(
        "--dataset",
        choices=[*DATASETS, "all"],
        default="all",
        help="Dataset to fetch (default: all)",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=500,
        help="Number of records per API page (default: 500)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Seconds to wait between API requests (default: 1.0)",
    )
    args = parser.parse_args()

    if not args.token:
        parser.error("Token required: use --token or set IAPH_API_TOKEN env var")

    targets = list(DATASETS.keys()) if args.dataset == "all" else [args.dataset]
    asyncio.run(main(args.token, targets, args.page_size, args.delay))


if __name__ == "__main__":
    cli()
