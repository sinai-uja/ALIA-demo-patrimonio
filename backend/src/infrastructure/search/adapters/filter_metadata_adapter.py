import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.domain.search.ports.filter_metadata_port import FilterMetadataPort

logger = logging.getLogger("iaph.search")


class PgFilterMetadataAdapter(FilterMetadataPort):
    """Retrieves distinct filter values from the chunks table."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._table = settings.chunks_table_name

    async def get_distinct_provinces(self) -> list[str]:
        query = text(f"""
            SELECT DISTINCT province
            FROM {self._table}
            WHERE province IS NOT NULL
            ORDER BY province ASC
        """)
        result = await self._db.execute(query)
        rows = result.fetchall()
        logger.info("Distinct provinces: %d", len(rows))
        return [row[0] for row in rows]

    async def get_distinct_municipalities(
        self, province: str | None = None,
    ) -> list[str]:
        query = text(f"""
            SELECT DISTINCT municipality
            FROM {self._table}
            WHERE municipality IS NOT NULL
              AND (
                  CAST(:province AS VARCHAR) IS NULL
                  OR province = :province
              )
            ORDER BY municipality ASC
        """)
        result = await self._db.execute(
            query, {"province": province},
        )
        rows = result.fetchall()
        logger.info(
            "Distinct municipalities (province=%s): %d",
            province,
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
