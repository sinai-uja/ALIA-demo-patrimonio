from src.application.rag.dto.rag_dto import RAGQueryDTO
from src.application.rag.services.rag_application_service import RAGApplicationService
from src.domain.chat.ports.rag_port import RAGPort


class InProcessRAGAdapter(RAGPort):
    """Adapts the RAG application service to satisfy the chat domain RAGPort.

    This keeps hexagonal purity: the chat domain depends on its own port,
    not on the RAG application service directly.
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
        dto = RAGQueryDTO(
            query=question,
            top_k=top_k,
            heritage_type_filter=heritage_type_filter,
            province_filter=province_filter,
        )
        result = await self._rag_service.query(dto)

        sources = [
            {
                "title": s.title,
                "url": s.url,
                "score": s.score,
                "heritage_type": s.heritage_type,
                "province": s.province,
            }
            for s in result.sources
        ]

        return result.answer, sources
