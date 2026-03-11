from src.application.routes.dto.routes_dto import RouteStopDTO, VirtualRouteDTO
from src.domain.routes.ports.route_repository import RouteRepository


class ListRoutesUseCase:
    """Lists virtual routes, optionally filtered by province."""

    def __init__(self, route_repository: RouteRepository) -> None:
        self._route_repository = route_repository

    async def execute(self, province: str | None = None) -> list[VirtualRouteDTO]:
        routes = await self._route_repository.list_routes(province)
        return [
            VirtualRouteDTO(
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
                    )
                    for stop in route.stops
                ],
                total_duration_minutes=route.total_duration_minutes,
                narrative=route.narrative,
                created_at=route.created_at.isoformat(),
            )
            for route in routes
        ]
