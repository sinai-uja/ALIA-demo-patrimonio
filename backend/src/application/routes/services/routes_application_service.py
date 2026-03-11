from src.application.routes.dto.routes_dto import (
    GenerateRouteDTO,
    GuideQueryDTO,
    GuideResponseDTO,
    VirtualRouteDTO,
)
from src.application.routes.use_cases.generate_route import GenerateRouteUseCase
from src.application.routes.use_cases.get_route import GetRouteUseCase
from src.application.routes.use_cases.guide_query import GuideQueryUseCase
from src.application.routes.use_cases.list_routes import ListRoutesUseCase


class RoutesApplicationService:
    """Application service that exposes route operations to the API layer."""

    def __init__(
        self,
        generate_route_use_case: GenerateRouteUseCase,
        guide_query_use_case: GuideQueryUseCase,
        list_routes_use_case: ListRoutesUseCase,
        get_route_use_case: GetRouteUseCase,
    ) -> None:
        self._generate_route = generate_route_use_case
        self._guide_query = guide_query_use_case
        self._list_routes = list_routes_use_case
        self._get_route = get_route_use_case

    async def generate_route(self, dto: GenerateRouteDTO) -> VirtualRouteDTO:
        return await self._generate_route.execute(dto)

    async def guide_query(self, dto: GuideQueryDTO) -> GuideResponseDTO:
        return await self._guide_query.execute(dto)

    async def list_routes(self, province: str | None = None) -> list[VirtualRouteDTO]:
        return await self._list_routes.execute(province)

    async def get_route(self, route_id: str) -> VirtualRouteDTO:
        return await self._get_route.execute(route_id)
