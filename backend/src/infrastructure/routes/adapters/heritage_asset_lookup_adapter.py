import logging
import re

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.routes.ports.heritage_asset_lookup_port import (
    HeritageAssetLookupPort,
)
from src.domain.routes.value_objects.asset_preview import AssetPreview

logger = logging.getLogger("iaph.routes")

_PREFIX_RE = re.compile(r"^ficha-\w+-")


def extract_asset_id(document_id: str) -> str:
    """Extract the numeric heritage asset ID from a chunk document_id.

    Chunk document_ids use the format 'ficha-{type}-{number}' while
    heritage_assets.id stores just the numeric part.
    """
    return _PREFIX_RE.sub("", document_id)


class PgHeritageAssetLookupAdapter(HeritageAssetLookupPort):
    """Fetches heritage asset preview data from the heritage_assets table."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_asset_previews(
        self, asset_ids: list[str],
    ) -> dict[str, AssetPreview]:
        if not asset_ids:
            return {}

        unique_ids = list(set(asset_ids))
        placeholders = ", ".join(f":id_{i}" for i in range(len(unique_ids)))
        params = {f"id_{i}": v for i, v in enumerate(unique_ids)}

        query = text(f"""
            SELECT id, latitude, longitude, image_url,
                   image_ids[1] AS first_image_id,
                   COALESCE(
                       NULLIF(TRIM(raw_data->>'clob.descripcion_s'), ''),
                       NULLIF(TRIM(raw_data->>'clob.desarrollo_s'), ''),
                       NULLIF(TRIM(raw_data->>'clob.origenes_s'), ''),
                       NULLIF(TRIM(raw_data->>'clob.desc_espacio_s'), ''),
                       NULLIF(TRIM(raw_data->>'identifica.dat_historico_s'), ''),
                       NULLIF(TRIM(raw_data->>'identifica.tipologias_s'), ''),
                       NULLIF(TRIM(raw_data->>'identifica.caracterizacion_s'), '')
                   ) AS description,
                   municipality
            FROM heritage_assets
            WHERE id IN ({placeholders})
        """)
        result = await self._db.execute(query, params)
        rows = result.fetchall()

        logger.info(
            "Heritage asset preview lookup: requested=%d, found=%d",
            len(unique_ids), len(rows),
        )

        previews: dict[str, AssetPreview] = {}
        for row in rows:
            asset_id = row[0]
            first_image_id = row[4]
            description = row[5]
            municipality = row[6]
            image_url = (
                f"https://guiadigital.iaph.es/imagenes-cache/"
                f"{asset_id}/{first_image_id}--fic.jpg"
                if first_image_id
                else None
            )
            previews[asset_id] = AssetPreview(
                id=asset_id,
                image_url=image_url,
                latitude=row[1],
                longitude=row[2],
                description=description,
                municipality=municipality,
            )

        return previews
