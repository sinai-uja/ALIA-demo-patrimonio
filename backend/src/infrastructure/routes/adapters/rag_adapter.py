import logging

from src.application.rag.dto.rag_dto import RAGQueryDTO
from src.application.rag.services.rag_application_service import (
    RAGApplicationService,
)
from src.domain.routes.ports.rag_port import RAGPort

logger = logging.getLogger("iaph.routes.rag")


class InProcessRAGAdapter(RAGPort):
    """Adapts the RAG application service to the routes RAGPort interface.

    Uses in-process delegation rather than HTTP to avoid unnecessary
    network overhead when both contexts live in the same process.
    """

    def __init__(self, rag_service: RAGApplicationService) -> None:
        self._rag_service = rag_service

    async def query(
        self,
        question: str,
        top_k: int,
        heritage_type_filter: list[str] | None = None,
        province_filter: list[str] | None = None,
        municipality_filter: list[str] | None = None,
    ) -> tuple[str, list[dict]]:
        logger.info(
            "RAG query start question=%r top_k=%d heritage_type=%r province=%r municipality=%r",
            question[:80], top_k, heritage_type_filter, province_filter, municipality_filter,
        )
        h_filter = (
            heritage_type_filter[0]
            if heritage_type_filter and len(heritage_type_filter) == 1
            else None
        )
        p_filter = (
            province_filter[0]
            if province_filter and len(province_filter) == 1
            else None
        )
        m_filter = (
            municipality_filter[0]
            if municipality_filter and len(municipality_filter) == 1
            else None
        )
        dto = RAGQueryDTO(
            query=question,
            top_k=top_k,
            heritage_type_filter=h_filter,
            province_filter=p_filter,
            municipality_filter=m_filter,
        )

        try:
            result = await self._rag_service.query(dto)
        except Exception:
            logger.error(
                "RAG query failed question=%r top_k=%d",
                question[:80], top_k, exc_info=True,
            )
            raise

        sources = [
            {
                "title": source.title,
                "url": source.url,
                "score": source.score,
                "heritage_type": source.heritage_type,
                "province": source.province,
                "municipality": source.municipality,
                "document_id": source.document_id,
                "content": source.content,
            }
            for source in result.sources
        ]

        return result.answer, sources
