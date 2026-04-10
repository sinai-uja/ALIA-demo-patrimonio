import logging

from fastapi import APIRouter, Depends

from src.api.v1.endpoints.auth.deps import get_current_user
from src.api.v1.endpoints.rag.deps import get_rag_service
from src.api.v1.endpoints.rag.schemas import QueryRequest, QueryResponse, SourceSchema
from src.application.rag.dto.rag_dto import RAGQueryDTO
from src.application.rag.services.rag_application_service import RAGApplicationService
from src.domain.auth.entities.user import User

logger = logging.getLogger("iaph.rag.router")

router = APIRouter()


@router.post("/query", response_model=QueryResponse)
async def rag_query(
    request: QueryRequest,
    user: User = Depends(get_current_user),
    service: RAGApplicationService = Depends(get_rag_service),
) -> QueryResponse:
    """Execute a RAG query: embed -> search -> assemble context -> generate answer."""
    logger.info(
        "POST /rag/query query=%r, top_k=%d, heritage_type=%s, province=%s",
        request.query[:80], request.top_k,
        request.heritage_type_filter, request.province_filter,
    )

    dto = RAGQueryDTO(
        query=request.query,
        top_k=request.top_k,
        heritage_type_filter=request.heritage_type_filter,
        province_filter=request.province_filter,
    )

    result = await service.query(dto)

    sources = [
        SourceSchema(
            title=s.title,
            url=s.url,
            score=s.score,
            heritage_type=s.heritage_type,
            province=s.province,
        )
        for s in result.sources
    ]

    logger.info(
        "RAG response: %d chars, %d sources, abstained=%s",
        len(result.answer), len(sources), result.abstained,
    )

    return QueryResponse(
        answer=result.answer,
        sources=sources,
        query=result.query,
        abstained=result.abstained,
    )
