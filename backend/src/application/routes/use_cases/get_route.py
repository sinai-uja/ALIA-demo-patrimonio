from uuid import UUID

from src.application.routes.dto.routes_dto import RouteStopDTO, VirtualRouteDTO
from src.domain.routes.ports.route_repository import RouteRepository


class GetRouteUseCase:
    """Retrieves a single virtual route by ID."""

    def __init__(self, route_repository: RouteRepository) -> None:
        self._route_repository = route_repository

    async def execute(self, route_id: str) -> VirtualRouteDTO:
        route = await self._route_repository.get_route(UUID(route_id))
        if route is None:
            raise ValueError(f"Route not found: {route_id}")

        return VirtualRouteDTO(
            id=str(route.id),
            title=route.title,
            province=route.province,
            stops=[
                RouteStopDTO(
                    order=stop.order,
                    title=stop.title,
                    heritage_type=stop.heritage_type,
                    province=stop.province,
                    municipality=stop.municipality,
                    url=stop.url,
                    description=stop.description,
                    visit_duration_minutes=stop.visit_duration_minutes,
                    heritage_asset_id=stop.heritage_asset_id,
                    narrative_segment=stop.narrative_segment,
                    image_url=stop.image_url,
                    latitude=stop.latitude,
                    longitude=stop.longitude,
                )
                for stop in route.stops
            ],
            total_duration_minutes=route.total_duration_minutes,
            narrative=route.narrative,
            introduction=route.introduction,
            conclusion=route.conclusion,
            created_at=route.created_at.isoformat(),
        )
