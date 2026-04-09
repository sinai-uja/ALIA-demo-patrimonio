import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.search.ports.heritage_asset_lookup_port import (
    HeritageAssetLookupPort,
    HeritageAssetSummaryData,
)
from src.domain.shared.value_objects.asset_id import extract_asset_id

logger = logging.getLogger("iaph.search.heritage_lookup")


class PgHeritageAssetLookupAdapter(HeritageAssetLookupPort):
    """Fetches heritage asset summaries by ID from the heritage_assets table."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_summaries_by_ids(
        self, ids: list[str],
    ) -> dict[str, HeritageAssetSummaryData]:
        if not ids:
            return {}

        # Map document_id -> asset_id for the query
        doc_to_asset = {doc_id: extract_asset_id(doc_id) for doc_id in ids}
        asset_ids = list(set(doc_to_asset.values()))

        placeholders = ", ".join(f":id_{i}" for i in range(len(asset_ids)))
        params = {f"id_{i}": v for i, v in enumerate(asset_ids)}

        query = text(f"""
            SELECT id, denomination, province, municipality,
                   COALESCE(
                       NULLIF(TRIM(raw_data->>'clob.descripcion_s'), ''),
                       NULLIF(TRIM(raw_data->>'clob.desarrollo_s'), ''),
                       NULLIF(TRIM(raw_data->>'clob.origenes_s'), ''),
                       NULLIF(TRIM(raw_data->>'clob.desc_espacio_s'), ''),
                       NULLIF(TRIM(raw_data->>'identifica.dat_historico_s'), ''),
                       NULLIF(TRIM(raw_data->>'identifica.tipologias_s'), ''),
                       NULLIF(TRIM(raw_data->>'identifica.caracterizacion_s'), '')
                   ) AS description,
                   latitude, longitude, image_url, protection,
                   image_ids[1] AS first_image_id
            FROM heritage_assets
            WHERE id IN ({placeholders})
        """)
        result = await self._db.execute(query, params)
        rows = result.fetchall()

        logger.info("Heritage asset lookup: requested=%d, found=%d", len(ids), len(rows))

        # Index by asset_id
        asset_by_id = {}
        for row in rows:
            asset_id = row[0]
            first_image_id = row[9]
            image_url = (
                f"https://guiadigital.iaph.es/imagenes-cache/"
                f"{asset_id}/{first_image_id}--fic.jpg"
                if first_image_id
                else None
            )
            asset_by_id[asset_id] = HeritageAssetSummaryData(
                id=asset_id,
                denomination=row[1],
                province=row[2],
                municipality=row[3],
                description=row[4],
                latitude=row[5],
                longitude=row[6],
                image_url=image_url,
                protection=row[8],
            )

        # Return indexed by original document_id so the use case can .get()
        return {
            doc_id: asset_by_id[asset_id]
            for doc_id, asset_id in doc_to_asset.items()
            if asset_id in asset_by_id
        }
