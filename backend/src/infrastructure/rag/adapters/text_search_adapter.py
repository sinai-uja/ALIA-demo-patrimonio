import logging
import re

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.domain.rag.entities.retrieved_chunk import RetrievedChunk
from src.domain.rag.ports.text_search_port import TextSearchPort

logger = logging.getLogger("iaph.query")

# Common Spanish stopwords and conversational verbs to strip before FTS
_STOPWORDS = {
    "de", "del", "la", "el", "los", "las", "un", "una", "en", "y", "a",
    "que", "es", "por", "con", "para", "al", "se", "lo", "como", "sobre",
    "dame", "dime", "hablame", "háblame", "cuentame", "cuéntame",
    "informacion", "información", "quiero", "saber", "necesito",
    "me", "te", "nos", "les", "su", "mi", "tu", "este", "esta",
    "ese", "esa", "aquel", "aquella", "mas", "más", "muy", "tan",
    "o", "u", "ni", "pero", "sino", "no", "si", "sí",
}


def _build_filter_conditions(
    heritage_type: str | list[str] | None,
    province: str | list[str] | None,
    municipality: str | list[str] | None,
) -> tuple[list[str], dict]:
    """Build dynamic WHERE conditions supporting single values or lists (OR)."""
    conditions: list[str] = []
    params: dict = {}
    for col, value, key in [
        ("heritage_type", heritage_type, "heritage_type"),
        ("province", province, "province"),
        ("municipality", municipality, "municipality"),
    ]:
        if value is None:
            continue
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


class PgTextSearchAdapter(TextSearchPort):
    """Full-text search using PostgreSQL tsvector."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._table = settings.chunks_table_name
        self._has_metadata = settings.chunks_table_version >= "v3"

    async def search(
        self,
        query: str,
        top_k: int,
        heritage_type: str | list[str] | None = None,
        province: str | list[str] | None = None,
        municipality: str | list[str] | None = None,
    ) -> list[RetrievedChunk]:
        clean_query = self._clean_query(query)
        if not clean_query:
            logger.info("FTS: empty query after cleaning, skipping")
            return []

        metadata_col = ", metadata" if self._has_metadata else ""
        conditions, params = _build_filter_conditions(
            heritage_type, province, municipality,
        )
        where_extra = (" AND " + " AND ".join(conditions)) if conditions else ""

        sql = text(f"""
            SELECT
                id,
                document_id,
                title,
                heritage_type,
                province,
                municipality,
                url,
                content,
                ts_rank_cd(
                    search_vector,
                    plainto_tsquery('spanish', :query)
                ) AS score
                {metadata_col}
            FROM {self._table}
            WHERE search_vector @@ plainto_tsquery('spanish', :query)
              {where_extra}
            ORDER BY score DESC
            LIMIT :top_k
        """)

        params["query"] = clean_query
        params["top_k"] = top_k

        result = await self._db.execute(sql, params)

        rows = result.fetchall()
        logger.info(
            "FTS: query=%r, heritage_type=%s, province=%s, "
            "municipality=%s → %d results",
            clean_query, heritage_type, province, municipality, len(rows),
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

    @staticmethod
    def _clean_query(query: str) -> str:
        """Remove stopwords and short tokens to improve FTS precision."""
        words = re.findall(r"\w+", query.lower())
        meaningful = [
            w for w in words if w not in _STOPWORDS and len(w) > 1
        ]
        return " ".join(meaningful)
