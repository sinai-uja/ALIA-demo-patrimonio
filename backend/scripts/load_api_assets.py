"""Load heritage assets from IAPH API JSON files (ZIP) into the heritage_assets table.

Usage:
    cd backend
    uv run python -m scripts.load_api_assets --source ../data/API_IAPH.zip
    uv run python -m scripts.load_api_assets --source ../data/API_IAPH.zip --dataset inmueble
"""

import argparse
import asyncio
import json
import logging
import time
import zipfile

from sqlalchemy import text as sql_text
from src.infrastructure.shared.persistence.engine import AsyncSessionLocal

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

# Maps ZIP filename → heritage_type value
DATASETS = {
    "inmueble.json": "inmueble",
    "mueble.json": "mueble",
    "inmaterial.json": "inmaterial",
    "paisaje.json": "paisaje",
}

# Field extraction per heritage type (API field → common column)
# Note: API "longitud_s" is actually latitude, "latitud_s" is actually longitude (confirmed bug)


def _extract_common_fields(doc: dict, heritage_type: str) -> dict:
    """Extract common columns from an API document based on its heritage type."""
    asset_id = str(doc.get("id", ""))

    if heritage_type == "inmueble":
        return {
            "id": asset_id,
            "heritage_type": heritage_type,
            "denomination": doc.get("identifica.denominacion_s"),
            "province": doc.get("identifica.provincia_s"),
            "municipality": doc.get("identifica.municipio_s"),
            # Names are swapped in the API (confirmed in README)
            "latitude": _safe_float(doc.get("longitud_s")),
            "longitude": _safe_float(doc.get("latitud_s")),
            "image_url": _first_image_url(doc),
            "image_ids": doc.get("imagen.id_img_smv"),
            "protection": doc.get("proteccion_s"),
        }
    elif heritage_type == "mueble":
        return {
            "id": asset_id,
            "heritage_type": heritage_type,
            "denomination": doc.get("identifica.denominacion_s") or doc.get("denominacion"),
            "province": doc.get("identifica.provincia_s") or doc.get("provincia"),
            "municipality": doc.get("identifica.municipio_s") or doc.get("municipio"),
            "latitude": None,
            "longitude": None,
            "image_url": _first_image_url(doc),
            "image_ids": doc.get("imagen.id_img_smv"),
            "protection": doc.get("proteccion_s"),
        }
    elif heritage_type == "inmaterial":
        return {
            "id": asset_id,
            "heritage_type": heritage_type,
            "denomination": doc.get("identifica.denominacion_s") or doc.get("denominacion"),
            "province": doc.get("identifica.provincia_s"),
            "municipality": doc.get("identifica.municipio_s"),
            "latitude": None,
            "longitude": None,
            "image_url": _first_image_url(doc),
            "image_ids": doc.get("imagen.id_img_smv"),
            "protection": doc.get("proteccion_s"),
        }
    elif heritage_type == "paisaje":
        return {
            "id": asset_id,
            "heritage_type": heritage_type,
            "denomination": doc.get("titulo"),
            "province": doc.get("provincia"),
            "municipality": None,
            "latitude": None,
            "longitude": None,
            "image_url": doc.get("imagen_url"),
            "image_ids": None,
            "protection": None,
        }
    return {"id": asset_id, "heritage_type": heritage_type}


def _safe_float(value) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _first_image_url(doc: dict) -> str | None:
    """Build image URL from first image UUID if available."""
    ids = doc.get("imagen.id_img_smv")
    if ids and len(ids) > 0:
        return f"https://guiadigital.iaph.es/sites/default/files/{ids[0]}"
    return None


def _clean_raw_data(doc: dict) -> dict:
    """Remove heavy fields (base64 images) from raw_data to save storage."""
    cleaned = {}
    for k, v in doc.items():
        if k == "imagen_base64":
            continue  # Skip base64 images (~100KB each)
        if k == "_version_":
            continue  # Solr internal
        cleaned[k] = v
    return cleaned


async def load_dataset(zip_path: str, filename: str, heritage_type: str) -> int:
    """Load a single dataset from the ZIP into heritage_assets."""
    logger.info("Loading %s from %s...", filename, zip_path)
    start = time.time()

    with zipfile.ZipFile(zip_path) as z:
        raw = z.read(filename)
    data = json.loads(raw)

    # Handle Solr response format
    docs = data.get("response", {}).get("docs", data if isinstance(data, list) else [])
    logger.info("Parsed %d documents from %s", len(docs), filename)

    upsert_sql = sql_text("""
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

    batch_size = 500
    total = 0

    async with AsyncSessionLocal() as db:
        for i in range(0, len(docs), batch_size):
            batch = docs[i : i + batch_size]
            params = []
            for doc in batch:
                common = _extract_common_fields(doc, heritage_type)
                common["raw_data"] = json.dumps(_clean_raw_data(doc))
                params.append(common)

            for p in params:
                await db.execute(upsert_sql, p)

            total += len(batch)
            if total % 5000 == 0:
                logger.info("  %s: %d / %d", heritage_type, total, len(docs))

        await db.commit()

    elapsed = time.time() - start
    logger.info("Done %s: %d assets loaded (%.1fs)", heritage_type, total, elapsed)
    return total


async def main(zip_path: str, datasets: dict[str, str]) -> None:
    grand_total = 0
    for filename, heritage_type in datasets.items():
        count = await load_dataset(zip_path, filename, heritage_type)
        grand_total += count
    logger.info("Grand total: %d assets loaded", grand_total)


def cli() -> None:
    parser = argparse.ArgumentParser(
        description="Load IAPH API JSON data into heritage_assets table.",
    )
    parser.add_argument(
        "--source",
        default="../data/API_IAPH.zip",
        help="Path to API_IAPH.zip (default: ../data/API_IAPH.zip)",
    )
    parser.add_argument(
        "--dataset",
        choices=[*DATASETS.values(), "all"],
        default="all",
        help="Dataset to load (default: all)",
    )
    args = parser.parse_args()

    if args.dataset == "all":
        targets = DATASETS
    else:
        targets = {k: v for k, v in DATASETS.items() if v == args.dataset}

    asyncio.run(main(args.source, targets))


if __name__ == "__main__":
    cli()
