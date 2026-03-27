import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from src.api.v1.endpoints.auth.deps import get_current_user
from src.api.v1.endpoints.search.deps import get_search_service
from src.api.v1.endpoints.search.schemas import (
    ChunkHitSchema,
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
from src.domain.auth.entities.user import User

logger = logging.getLogger("iaph.usecases.search")

router = APIRouter()


@router.post("/similarity", response_model=SimilaritySearchResponse)
async def similarity_search(
    request: SimilaritySearchRequest,
    user: User = Depends(get_current_user),
    service: SearchApplicationService = Depends(get_search_service),
) -> SimilaritySearchResponse:
    """Execute a similarity search: embed, search, fuse, filter, rerank."""
    logger.info(
        "POST /search/similarity query=%r, page=%d, page_size=%d",
        request.query[:80],
        request.page,
        request.page_size,
    )

    dto = SimilaritySearchDTO(
        query=request.query,
        page=request.page,
        page_size=request.page_size,
        heritage_type_filter=request.heritage_type_filter,
        province_filter=request.province_filter,
        municipality_filter=request.municipality_filter,
        user_id=user.username,
    )

    try:
        result = await service.similarity_search(dto)
    except Exception as exc:
        logger.error("Search pipeline failed: query=%r, error=%s", request.query[:80], exc)
        raise HTTPException(
            status_code=502,
            detail=f"Search pipeline error: {exc}",
        ) from exc

    logger.info(
        "Search response: search_id=%s query=%r, total_results=%d, page=%d/%d",
        result.search_id, request.query[:80], result.total_results,
        result.page, result.total_pages,
    )
    return SimilaritySearchResponse(
        results=[
            SearchResultSchema(
                document_id=r.document_id,
                title=r.title,
                heritage_type=r.heritage_type,
                province=r.province,
                municipality=r.municipality,
                url=r.url,
                best_score=r.best_score,
                chunks=[
                    ChunkHitSchema(
                        chunk_id=c.chunk_id,
                        content=c.content,
                        score=c.score,
                    )
                    for c in r.chunks
                ],
                denomination=r.denomination,
                description=r.description,
                latitude=r.latitude,
                longitude=r.longitude,
                image_url=r.image_url,
                protection=r.protection,
            )
            for r in result.results
        ],
        query=result.query,
        total_results=result.total_results,
        page=result.page,
        page_size=result.page_size,
        total_pages=result.total_pages,
        search_id=result.search_id,
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
                matched_text=e.matched_text,
            )
            for e in result.detected_entities
        ],
    )


@router.get("/filters", response_model=FilterValuesResponse)
async def get_filters(
    province: list[str] | None = Query(
        default=None,
        description="Filter municipalities by province(s)",
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
