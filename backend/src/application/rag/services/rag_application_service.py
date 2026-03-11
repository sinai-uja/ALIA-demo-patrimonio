from src.application.rag.dto.rag_dto import RAGQueryDTO, RAGResponseDTO
from src.application.rag.use_cases.rag_query_use_case import RAGQueryUseCase


class RAGApplicationService:
    """Application service that exposes RAG operations to the API layer."""

    def __init__(self, rag_query_use_case: RAGQueryUseCase) -> None:
        self._rag_query_use_case = rag_query_use_case

    async def query(self, dto: RAGQueryDTO) -> RAGResponseDTO:
        return await self._rag_query_use_case.execute(dto)
