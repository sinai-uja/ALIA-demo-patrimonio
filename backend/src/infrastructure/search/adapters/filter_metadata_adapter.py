import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.domain.search.ports.filter_metadata_port import FilterMetadataPort

logger = logging.getLogger("iaph.search.filter_metadata")


class PgFilterMetadataAdapter(FilterMetadataPort):
    """Retrieves distinct filter values from heritage_assets for
    provinces/municipalities and from chunks for heritage types."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._table = settings.chunks_table_name

    async def get_distinct_provinces(self) -> list[str]:
        query = text("""
            SELECT DISTINCT province
            FROM heritage_assets
            WHERE province IS NOT NULL
            ORDER BY province ASC
        """)
        result = await self._db.execute(query)
        rows = result.fetchall()
        logger.info("Distinct provinces: %d", len(rows))
        return [row[0] for row in rows]

    async def get_distinct_municipalities(
        self, provinces: list[str] | None = None,
    ) -> list[str]:
        params: dict = {}
        if provinces:
            placeholders = ", ".join(
                f":province_{i}" for i in range(len(provinces))
            )
            province_filter = f"AND province IN ({placeholders})"
            for i, v in enumerate(provinces):
                params[f"province_{i}"] = v
        else:
            province_filter = ""

        query = text(f"""
            SELECT DISTINCT municipality
            FROM heritage_assets
            WHERE municipality IS NOT NULL
              {province_filter}
            ORDER BY municipality ASC
        """)
        result = await self._db.execute(query, params)
        rows = result.fetchall()
        logger.info(
            "Distinct municipalities (provinces=%s): %d",
            provinces,
            len(rows),
        )
        return [row[0] for row in rows]

    async def get_distinct_heritage_types(self) -> list[str]:
        query = text(f"""
            SELECT DISTINCT heritage_type
            FROM {self._table}
            WHERE heritage_type IS NOT NULL
            ORDER BY heritage_type ASC
        """)
        result = await self._db.execute(query)
        rows = result.fetchall()
        logger.info("Distinct heritage types: %d", len(rows))
        return [row[0] for row in rows]
