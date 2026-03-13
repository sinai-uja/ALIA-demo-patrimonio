import re

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.rag.entities.retrieved_chunk import RetrievedChunk
from src.domain.rag.ports.text_search_port import TextSearchPort

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


class PgTextSearchAdapter(TextSearchPort):
    """Full-text search using PostgreSQL tsvector on document_chunks table."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def search(
        self,
        query: str,
        top_k: int,
        heritage_type: str | None = None,
        province: str | None = None,
    ) -> list[RetrievedChunk]:
        clean_query = self._clean_query(query)
        if not clean_query:
            return []

        sql = text("""
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
            FROM document_chunks
            WHERE search_vector @@ plainto_tsquery('spanish', :query)
              AND (
                CAST(:heritage_type AS VARCHAR) IS NULL
                OR heritage_type = :heritage_type
              )
              AND (
                CAST(:province AS VARCHAR) IS NULL
                OR province = :province
              )
            ORDER BY score DESC
            LIMIT :top_k
        """)

        result = await self._db.execute(
            sql,
            {
                "query": clean_query,
                "heritage_type": heritage_type,
                "province": province,
                "top_k": top_k,
            },
        )

        rows = result.fetchall()

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
