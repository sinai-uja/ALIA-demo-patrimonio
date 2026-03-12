from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.rag.entities.retrieved_chunk import RetrievedChunk
from src.domain.rag.ports.vector_search_port import VectorSearchPort


class PgVectorSearchAdapter(VectorSearchPort):
    """Vector similarity search using pgvector cosine distance on document_chunks table."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def search(
        self,
        query_embedding: list[float],
        top_k: int,
        heritage_type: str | None = None,
        province: str | None = None,
    ) -> list[RetrievedChunk]:
        query = text("""
            SELECT
                id,
                document_id,
                title,
                heritage_type,
                province,
                municipality,
                url,
                content,
                embedding <=> :query_vec AS score
            FROM document_chunks
            WHERE (CAST(:heritage_type AS VARCHAR) IS NULL OR heritage_type = :heritage_type)
              AND (CAST(:province AS VARCHAR) IS NULL OR province = :province)
            ORDER BY score ASC
            LIMIT :top_k
        """)

        embedding_str = "[" + ",".join(str(v) for v in query_embedding) + "]"

        result = await self._db.execute(
            query,
            {
                "query_vec": embedding_str,
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
