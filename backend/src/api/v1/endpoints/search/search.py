import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from src.api.v1.endpoints.search.deps import get_search_service
from src.api.v1.endpoints.search.schemas import (
    DetectedEntitySchema,
    FilterValuesResponse,
    SearchResultSchema,
    SimilaritySearchRequest,
    SimilaritySearchResponse,
    SuggestionResponse,
)
from src.application.search.dto.search_dto import SimilaritySearchDTO
from src.application.search.services.search_application_service import (
    SearchApplicationService,
)

logger = logging.getLogger("iaph.search")

router = APIRouter()


@router.post("/similarity", response_model=SimilaritySearchResponse)
async def similarity_search(
    request: SimilaritySearchRequest,
    service: SearchApplicationService = Depends(get_search_service),
) -> SimilaritySearchResponse:
    """Execute a similarity search: embed, search, fuse, filter, rerank."""
    logger.info(
        "POST /search/similarity query=%r, top_k=%d",
        request.query[:80],
        request.top_k,
    )

    dto = SimilaritySearchDTO(
        query=request.query,
        top_k=request.top_k,
        heritage_type_filter=request.heritage_type_filter,
        province_filter=request.province_filter,
        municipality_filter=request.municipality_filter,
    )

    try:
        result = await service.similarity_search(dto)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Search pipeline error: {exc}",
        ) from exc

    return SimilaritySearchResponse(
        results=[
            SearchResultSchema(
                chunk_id=r.chunk_id,
                document_id=r.document_id,
                title=r.title,
                heritage_type=r.heritage_type,
                province=r.province,
                municipality=r.municipality,
                url=r.url,
                content=r.content,
                score=r.score,
            )
            for r in result.results
        ],
        query=result.query,
        total_results=result.total_results,
    )


@router.get("/suggestions", response_model=SuggestionResponse)
async def get_suggestions(
    query: str = Query(
        ..., min_length=1, description="Search query text",
    ),
    service: SearchApplicationService = Depends(get_search_service),
) -> SuggestionResponse:
    """Detect entities in a search query and return suggestions."""
    logger.info("GET /search/suggestions query=%r", query[:80])

    try:
        result = await service.get_suggestions(query)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Suggestion error: {exc}",
        ) from exc

    return SuggestionResponse(
        query=result.query,
        search_label=result.search_label,
        detected_entities=[
            DetectedEntitySchema(
                entity_type=e.entity_type,
                value=e.value,
                display_label=e.display_label,
            )
            for e in result.detected_entities
        ],
    )


@router.get("/filters", response_model=FilterValuesResponse)
async def get_filters(
    province: str | None = Query(
        default=None,
        description="Filter municipalities by province",
    ),
    service: SearchApplicationService = Depends(get_search_service),
) -> FilterValuesResponse:
    """Return available filter values for search facets."""
    logger.info("GET /search/filters province=%s", province)

    try:
        result = await service.get_filter_values(province)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Filter values error: {exc}",
        ) from exc

    return FilterValuesResponse(
        heritage_types=result.heritage_types,
        provinces=result.provinces,
        municipalities=result.municipalities,
    )
