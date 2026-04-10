import logging

from src.application.rag.dto.rag_dto import RAGQueryDTO
from src.application.rag.services.rag_application_service import RAGApplicationService
from src.domain.chat.ports.rag_port import RAGPort

logger = logging.getLogger("iaph.chat.rag")


class InProcessRAGAdapter(RAGPort):
    """Adapts the RAG application service to satisfy the chat domain RAGPort.

    The chat domain depends on its own port; this adapter bridges to the
    RAG application service so the two bounded contexts stay decoupled.
    """

    def __init__(self, rag_service: RAGApplicationService) -> None:
        self._rag_service = rag_service

    async def query(
        self,
        question: str,
        top_k: int,
        heritage_type_filter: str | None,
        province_filter: str | None,
    ) -> tuple[str, list[dict]]:
        logger.info(
            "RAG query start question=%r top_k=%d heritage_type=%r province=%r",
            question[:80], top_k, heritage_type_filter, province_filter,
        )
        dto = RAGQueryDTO(
            query=question,
            top_k=top_k,
            heritage_type_filter=heritage_type_filter,
            province_filter=province_filter,
        )
        try:
            result = await self._rag_service.query(dto)
        except Exception:
            logger.error(
                "RAG query failed question=%r top_k=%d heritage_type=%r province=%r",
                question[:80], top_k, heritage_type_filter, province_filter, exc_info=True,
            )
            raise

        sources = [
            {
                "title": s.title,
                "url": s.url,
                "score": s.score,
                "heritage_type": s.heritage_type,
                "province": s.province,
                "municipality": s.municipality,
                "metadata": s.metadata,
            }
            for s in result.sources
        ]

        return result.answer, sources
