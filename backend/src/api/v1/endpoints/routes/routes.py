import logging

from fastapi import APIRouter, Depends, Query, Response

from src.api.v1.endpoints.auth.deps import get_current_user
from src.api.v1.endpoints.routes.deps import get_routes_service
from src.api.v1.endpoints.routes.schemas import (
    DetectedEntitySchema,
    GenerateRouteRequest,
    GuideQueryRequest,
    GuideResponseSchema,
    RouteFilterValuesResponse,
    RouteStopSchema,
    RouteSuggestionResponse,
    VirtualRouteSchema,
)
from src.application.routes.dto.history_turn_dto import HistoryTurnDTO
from src.application.routes.dto.routes_dto import (
    GenerateRouteDTO,
    GuideQueryDTO,
    VirtualRouteDTO,
)
from src.application.routes.services.routes_application_service import (
    RoutesApplicationService,
)
from src.domain.auth.entities.user import User

logger = logging.getLogger("iaph.routes.router")

router = APIRouter()


def _dto_to_schema(result: VirtualRouteDTO) -> VirtualRouteSchema:
    return VirtualRouteSchema(
        id=result.id,
        title=result.title,
        province=result.province,
        stops=[
            RouteStopSchema(
                order=s.order,
                title=s.title,
                heritage_type=s.heritage_type,
                province=s.province,
                municipality=s.municipality,
                url=s.url,
                description=s.description,

                heritage_asset_id=s.heritage_asset_id,
                narrative_segment=s.narrative_segment,
                image_url=s.image_url,
                latitude=s.latitude,
                longitude=s.longitude,
            )
            for s in result.stops
        ],

        narrative=result.narrative,
        introduction=result.introduction or None,
        conclusion=result.conclusion or None,
        created_at=result.created_at,
    )


@router.get(
    "/suggestions", response_model=RouteSuggestionResponse,
)
async def get_route_suggestions(
    query: str,
    user: User = Depends(get_current_user),
    service: RoutesApplicationService = Depends(get_routes_service),
) -> RouteSuggestionResponse:
    """Get entity-detection suggestions for a route planning query."""
    result = await service.get_suggestions(query)
    return RouteSuggestionResponse(
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


@router.get(
    "/filters", response_model=RouteFilterValuesResponse,
)
async def get_route_filters(
    province: list[str] | None = Query(default=None),
    user: User = Depends(get_current_user),
    service: RoutesApplicationService = Depends(get_routes_service),
) -> RouteFilterValuesResponse:
    """Get available filter values for route planning."""
    result = await service.get_filter_values(province)
    return RouteFilterValuesResponse(
        heritage_types=result.heritage_types,
        provinces=result.provinces,
        municipalities=result.municipalities,
    )


@router.post("/generate", response_model=VirtualRouteSchema)
async def generate_route(
    request: GenerateRouteRequest,
    user: User = Depends(get_current_user),
    service: RoutesApplicationService = Depends(get_routes_service),
) -> VirtualRouteSchema:
    """Generate a personalized virtual heritage route."""
    logger.info(
        "POST /routes/generate query=%r, num_stops=%d, "
        "heritage_type=%s, province=%s, municipality=%s",
        request.query[:80], request.num_stops or 5,
        request.heritage_type_filter, request.province_filter, request.municipality_filter,
    )
    dto = GenerateRouteDTO(
        query=request.query,
        num_stops=request.num_stops,
        heritage_type_filter=request.heritage_type_filter,
        province_filter=request.province_filter,
        municipality_filter=request.municipality_filter,
        user_id=str(user.id),
        username=user.username,
        user_profile_type=user.profile_type.name if user.profile_type else None,
    )

    result = await service.generate_route(dto)

    logger.info(
        "Route generated: id=%s, title=%r, stops=%d",
        result.id, result.title, len(result.stops),
    )
    return _dto_to_schema(result)


@router.get("", response_model=list[VirtualRouteSchema])
async def list_routes(
    province: str | None = None,
    user: User = Depends(get_current_user),
    service: RoutesApplicationService = Depends(get_routes_service),
) -> list[VirtualRouteSchema]:
    """List virtual routes, optionally filtered by province."""
    results = await service.list_routes(province, user_id=str(user.id))
    return [_dto_to_schema(r) for r in results]


@router.delete("/{route_id}", status_code=204)
async def delete_route(
    route_id: str,
    user: User = Depends(get_current_user),
    service: RoutesApplicationService = Depends(get_routes_service),
) -> Response:
    """Delete a virtual route by ID."""
    await service.delete_route(route_id, user_id=str(user.id))
    return Response(status_code=204)


@router.get("/{route_id}", response_model=VirtualRouteSchema)
async def get_route(
    route_id: str,
    user: User = Depends(get_current_user),
    service: RoutesApplicationService = Depends(get_routes_service),
) -> VirtualRouteSchema:
    """Get a specific virtual route by ID."""
    result = await service.get_route(route_id, user_id=str(user.id))
    return _dto_to_schema(result)


@router.post(
    "/{route_id}/guide", response_model=GuideResponseSchema,
)
async def guide_query(
    route_id: str,
    request: GuideQueryRequest,
    user: User = Depends(get_current_user),
    service: RoutesApplicationService = Depends(get_routes_service),
) -> GuideResponseSchema:
    """Ask the guide a question about a specific route."""
    logger.info(
        "POST /routes/%s/guide question=%r, history_len=%d",
        route_id, request.question[:80], len(request.history),
    )
    dto = GuideQueryDTO(
        route_id=route_id,
        question=request.question,
        history=[
            HistoryTurnDTO(role=m.role, content=m.content)
            for m in request.history
        ],
    )

    result = await service.guide_query(dto)

    logger.info(
        "Guide response: route=%s, answer=%d chars, sources=%d",
        route_id, len(result.answer), len(result.sources),
    )
    return GuideResponseSchema(
        answer=result.answer,
        sources=result.sources,
    )
