from fastapi import APIRouter, Depends, HTTPException

from src.api.v1.endpoints.rag.deps import get_rag_service
from src.api.v1.endpoints.rag.schemas import QueryRequest, QueryResponse, SourceSchema
from src.application.rag.dto.rag_dto import RAGQueryDTO
from src.application.rag.services.rag_application_service import RAGApplicationService

router = APIRouter()


@router.post("/query", response_model=QueryResponse)
async def rag_query(
    request: QueryRequest,
    service: RAGApplicationService = Depends(get_rag_service),
) -> QueryResponse:
    """Execute a RAG query: embed -> search -> assemble context -> generate answer."""
    dto = RAGQueryDTO(
        query=request.query,
        top_k=request.top_k,
        heritage_type_filter=request.heritage_type_filter,
        province_filter=request.province_filter,
    )

    try:
        result = await service.query(dto)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"RAG pipeline error: {exc}") from exc

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

    return QueryResponse(
        answer=result.answer,
        sources=sources,
        query=result.query,
        abstained=result.abstained,
    )
