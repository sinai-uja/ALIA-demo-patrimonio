from src.application.routes.dto.routes_dto import (
    GenerateRouteDTO,
    GuideQueryDTO,
    GuideResponseDTO,
    RouteFilterValuesDTO,
    RouteSuggestionResponseDTO,
    VirtualRouteDTO,
)
from src.application.routes.use_cases.generate_route import (
    GenerateRouteUseCase,
)
from src.application.routes.use_cases.get_route import GetRouteUseCase
from src.application.routes.use_cases.guide_query import GuideQueryUseCase
from src.application.routes.use_cases.list_routes import ListRoutesUseCase
from src.application.routes.use_cases.route_filter_values import (
    RouteFilterValuesUseCase,
)
from src.application.routes.use_cases.route_suggestions import (
    RouteSuggestionsUseCase,
)


class RoutesApplicationService:
    """Application service that exposes route operations to the API layer."""

    def __init__(
        self,
        generate_route_use_case: GenerateRouteUseCase,
        guide_query_use_case: GuideQueryUseCase,
        list_routes_use_case: ListRoutesUseCase,
        get_route_use_case: GetRouteUseCase,
        route_suggestions_use_case: RouteSuggestionsUseCase,
        route_filter_values_use_case: RouteFilterValuesUseCase,
    ) -> None:
        self._generate_route = generate_route_use_case
        self._guide_query = guide_query_use_case
        self._list_routes = list_routes_use_case
        self._get_route = get_route_use_case
        self._route_suggestions = route_suggestions_use_case
        self._route_filter_values = route_filter_values_use_case

    async def generate_route(
        self, dto: GenerateRouteDTO,
    ) -> VirtualRouteDTO:
        return await self._generate_route.execute(dto)

    async def guide_query(
        self, dto: GuideQueryDTO,
    ) -> GuideResponseDTO:
        return await self._guide_query.execute(dto)

    async def list_routes(
        self, province: str | None = None,
    ) -> list[VirtualRouteDTO]:
        return await self._list_routes.execute(province)

    async def get_route(self, route_id: str) -> VirtualRouteDTO:
        return await self._get_route.execute(route_id)

    async def get_suggestions(
        self, query: str,
    ) -> RouteSuggestionResponseDTO:
        return await self._route_suggestions.execute(query)

    async def get_filter_values(
        self, provinces: list[str] | None = None,
    ) -> RouteFilterValuesDTO:
        return await self._route_filter_values.execute(provinces)
