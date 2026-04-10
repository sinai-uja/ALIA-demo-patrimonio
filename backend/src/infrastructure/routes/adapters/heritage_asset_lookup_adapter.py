import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.routes.ports.heritage_asset_lookup_port import (
    HeritageAssetLookupPort,
)
from src.domain.routes.value_objects.asset_preview import AssetPreview

logger = logging.getLogger("iaph.routes.heritage_lookup")


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
        try:
            result = await self._db.execute(query, params)
        except Exception:
            logger.error("Failed to get asset previews count=%d", len(unique_ids), exc_info=True)
            raise
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

    async def get_asset_full_descriptions(
        self, asset_ids: list[str],
    ) -> dict[str, str]:
        if not asset_ids:
            return {}

        unique_ids = list(set(asset_ids))
        placeholders = ", ".join(f":id_{i}" for i in range(len(unique_ids)))
        params = {f"id_{i}": v for i, v in enumerate(unique_ids)}

        query = text(f"""
            SELECT
                id,
                denomination,
                municipality,
                province,
                protection,
                raw_data->>'clob.descripcion_s' AS descripcion,
                raw_data->>'clob.desarrollo_s' AS desarrollo,
                raw_data->>'clob.origenes_s' AS origenes,
                raw_data->>'clob.desc_espacio_s' AS desc_espacio,
                raw_data->>'clob.evolucion_s' AS evolucion,
                raw_data->>'identifica.dat_historico_s' AS dat_historico,
                raw_data->>'identifica.tipologias_s' AS tipologias,
                raw_data->>'identifica.caracterizacion_s' AS caracterizacion,
                raw_data->>'identifica.cronologia_s' AS cronologia
            FROM heritage_assets
            WHERE id IN ({placeholders})
        """)
        try:
            result = await self._db.execute(query, params)
        except Exception:
            logger.error("Failed to get asset full descriptions count=%d", len(unique_ids), exc_info=True)
            raise
        rows = result.fetchall()

        descriptions: dict[str, str] = {}
        for row in rows:
            sections: list[str] = []
            asset_id = row[0]

            if row[1]:  # denomination
                sections.append(f"Nombre oficial: {row[1]}")
            if row[2] or row[3]:  # municipality, province
                loc = ", ".join(filter(None, [row[2], row[3]]))
                sections.append(f"Ubicacion: {loc}")
            if row[4]:  # protection
                sections.append(f"Proteccion: {row[4]}")

            field_labels = [
                (5, "Descripcion"),
                (6, "Desarrollo"),
                (7, "Origenes"),
                (8, "Descripcion espacial"),
                (9, "Evolucion"),
                (10, "Datos historicos"),
                (11, "Tipologias"),
                (12, "Caracterizacion"),
                (13, "Cronologia"),
            ]
            for idx, label in field_labels:
                val = row[idx]
                if val and val.strip():
                    sections.append(f"{label}: {val.strip()}")

            descriptions[asset_id] = "\n\n".join(sections) if sections else ""

        logger.info(
            "Heritage asset full descriptions: requested=%d, found=%d",
            len(unique_ids), len(rows),
        )
        return descriptions
