from src.application.rag.dto.rag_dto import RAGQueryDTO
from src.application.rag.services.rag_application_service import RAGApplicationService
from src.domain.routes.ports.rag_port import RAGPort


class InProcessRAGAdapter(RAGPort):
    """Adapts the RAG application service to the routes RAGPort interface.

    Uses in-process delegation rather than HTTP to avoid unnecessary network
    overhead when both contexts live in the same process.
    """

    def __init__(self, rag_service: RAGApplicationService) -> None:
        self._rag_service = rag_service

    async def query(
        self,
        question: str,
        top_k: int,
        heritage_type_filter: str | None = None,
        province_filter: str | None = None,
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
                "title": source.title,
                "url": source.url,
                "score": source.score,
                "heritage_type": source.heritage_type,
                "province": source.province,
            }
            for source in result.sources
        ]

        return result.answer, sources
