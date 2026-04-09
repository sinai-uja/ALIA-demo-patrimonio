import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.domain.rag.entities.retrieved_chunk import RetrievedChunk
from src.domain.rag.ports.vector_search_port import VectorSearchPort

logger = logging.getLogger("iaph.query")


def _build_filter_conditions(
    heritage_type: str | list[str] | None,
    province: str | list[str] | None,
    municipality: str | list[str] | None,
    *,
    use_asset_join: bool = False,
) -> tuple[list[str], dict]:
    """Build dynamic WHERE conditions supporting single values or lists (OR).

    When *use_asset_join* is True the query includes a LEFT JOIN on
    ``heritage_assets`` so geographic filters use the authoritative asset
    data via ``COALESCE(ha.<col>, c.<col>)``.  ``heritage_type`` always
    filters on the chunks table because the two tables use different naming
    conventions (``patrimonio_inmueble`` vs ``inmueble``).
    """
    conditions: list[str] = []
    params: dict = {}

    col_map = {
        "heritage_type": "c.heritage_type" if use_asset_join else "heritage_type",
        "province": (
            "COALESCE(ha.province, c.province)" if use_asset_join else "province"
        ),
        "municipality": (
            "COALESCE(ha.municipality, c.municipality)" if use_asset_join else "municipality"
        ),
    }

    for key, value in [
        ("heritage_type", heritage_type),
        ("province", province),
        ("municipality", municipality),
    ]:
        if value is None:
            continue
        col = col_map[key]
        if isinstance(value, list):
            if not value:
                continue
            placeholders = ", ".join(f":{key}_{i}" for i in range(len(value)))
            conditions.append(f"{col} IN ({placeholders})")
            for i, v in enumerate(value):
                params[f"{key}_{i}"] = v
        else:
            conditions.append(f"{col} = :{key}")
            params[key] = value
    return conditions, params


class PgVectorSearchAdapter(VectorSearchPort):
    """Vector similarity search using pgvector cosine distance."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._table = settings.chunks_table_name
        self._has_metadata = settings.chunks_table_version >= "v3"

    async def search(
        self,
        query_embedding: list[float],
        top_k: int,
        heritage_type: str | list[str] | None = None,
        province: str | list[str] | None = None,
        municipality: str | list[str] | None = None,
    ) -> list[RetrievedChunk]:
        # JOIN heritage_assets only when geographic filters are present so that
        # province/municipality filtering uses the authoritative asset data.
        needs_asset_join = province is not None or municipality is not None

        conditions, params = _build_filter_conditions(
            heritage_type, province, municipality,
            use_asset_join=needs_asset_join,
        )
        where_clause = (" AND " + " AND ".join(conditions)) if conditions else ""

        if needs_asset_join:
            prefix = "c."
            metadata_col = ", c.metadata" if self._has_metadata else ""
            from_clause = (
                f"{self._table} c\n"
                "            LEFT JOIN heritage_assets ha\n"
                "                ON ha.id = regexp_replace(c.document_id,"
                " '^ficha-\\w+-', '')"
            )
        else:
            prefix = ""
            metadata_col = ", metadata" if self._has_metadata else ""
            from_clause = self._table

        # Ensure HNSW index explores enough candidates for the requested top_k
        await self._db.execute(
            text(f"SET LOCAL hnsw.ef_search = {max(top_k, 100)}"),
        )

        query = text(f"""
            SELECT
                {prefix}id,
                {prefix}document_id,
                {prefix}title,
                {prefix}heritage_type,
                {prefix}province,
                {prefix}municipality,
                {prefix}url,
                {prefix}content,
                {prefix}embedding <=> :query_vec AS score
                {metadata_col}
            FROM {from_clause}
            WHERE TRUE{where_clause}
            ORDER BY score ASC
            LIMIT :top_k
        """)

        embedding_str = "[" + ",".join(str(v) for v in query_embedding) + "]"
        params["query_vec"] = embedding_str
        params["top_k"] = top_k

        result = await self._db.execute(query, params)

        rows = result.fetchall()
        logger.info(
            "Vector search: top_k=%d, heritage_type=%s, province=%s, "
            "municipality=%s → %d results",
            top_k, heritage_type, province, municipality, len(rows),
        )

        return [
            RetrievedChunk(
                chunk_id=str(row.id),
                document_id=str(row.document_id),
                title=row.title,
                heritage_type=row.heritage_type,
                province=row.province,
                municipality=row.municipality,
                url=row.url,
                content=row.content,
                score=float(row.score),
                metadata=row.metadata if self._has_metadata else None,
            )
            for row in rows
        ]
