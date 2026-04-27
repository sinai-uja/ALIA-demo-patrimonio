from collections.abc import AsyncGenerator

from src.application.routes.dto.routes_dto import (
    GenerateRouteDTO,
    GuideQueryDTO,
    GuideResponseDTO,
    RouteFilterValuesDTO,
    RouteSuggestionResponseDTO,
    VirtualRouteDTO,
)
from src.application.routes.use_cases.add_stop import AddStopUseCase
from src.application.routes.use_cases.delete_route import (
    DeleteRouteUseCase,
)
from src.application.routes.use_cases.generate_route import (
    GenerateRouteUseCase,
)
from src.application.routes.use_cases.generate_route_stream import (
    GenerateRouteStreamUseCase,
)
from src.application.routes.use_cases.get_route import GetRouteUseCase
from src.application.routes.use_cases.guide_query import GuideQueryUseCase
from src.application.routes.use_cases.list_routes import ListRoutesUseCase
from src.application.routes.use_cases.remove_stop import RemoveStopUseCase
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
        delete_route_use_case: DeleteRouteUseCase,
        route_suggestions_use_case: RouteSuggestionsUseCase,
        route_filter_values_use_case: RouteFilterValuesUseCase,
        remove_stop_use_case: RemoveStopUseCase | None = None,
        add_stop_use_case: AddStopUseCase | None = None,
        generate_route_stream_use_case: GenerateRouteStreamUseCase | None = None,
    ) -> None:
        self._generate_route = generate_route_use_case
        self._guide_query = guide_query_use_case
        self._list_routes = list_routes_use_case
        self._get_route = get_route_use_case
        self._delete_route = delete_route_use_case
        self._route_suggestions = route_suggestions_use_case
        self._route_filter_values = route_filter_values_use_case
        self._remove_stop = remove_stop_use_case
        self._add_stop = add_stop_use_case
        self._generate_route_stream = generate_route_stream_use_case

    async def generate_route(
        self, dto: GenerateRouteDTO,
    ) -> VirtualRouteDTO:
        return await self._generate_route.execute(dto)

    async def guide_query(
        self, dto: GuideQueryDTO,
    ) -> GuideResponseDTO:
        return await self._guide_query.execute(dto)

    async def list_routes(
        self, province: str | None = None, user_id: str | None = None,
    ) -> list[VirtualRouteDTO]:
        return await self._list_routes.execute(province, user_id=user_id)

    async def get_route(self, route_id: str, user_id: str | None = None) -> VirtualRouteDTO:
        return await self._get_route.execute(route_id, user_id=user_id)

    async def delete_route(self, route_id: str, user_id: str | None = None) -> None:
        return await self._delete_route.execute(route_id, user_id=user_id)

    async def get_suggestions(
        self, query: str,
    ) -> RouteSuggestionResponseDTO:
        return await self._route_suggestions.execute(query)

    async def get_filter_values(
        self, provinces: list[str] | None = None,
    ) -> RouteFilterValuesDTO:
        return await self._route_filter_values.execute(provinces)

    async def remove_stop(
        self,
        route_id: str,
        stop_order: int,
        user_id: str | None = None,
        username: str | None = None,
        user_profile_type: str | None = None,
    ) -> VirtualRouteDTO:
        if self._remove_stop is None:
            raise RuntimeError("RemoveStopUseCase not wired")
        return await self._remove_stop.execute(
            route_id,
            stop_order,
            user_id=user_id,
            username=username,
            user_profile_type=user_profile_type,
        )

    async def add_stop(
        self,
        route_id: str,
        document_id: str,
        position: int | None = None,
        user_id: str | None = None,
        username: str | None = None,
        user_profile_type: str | None = None,
    ) -> VirtualRouteDTO:
        if self._add_stop is None:
            raise RuntimeError("AddStopUseCase not wired")
        return await self._add_stop.execute(
            route_id,
            document_id,
            position=position,
            user_id=user_id,
            username=username,
            user_profile_type=user_profile_type,
        )

    async def generate_route_stream(
        self, dto: GenerateRouteDTO,
    ) -> AsyncGenerator[dict, None]:
        if self._generate_route_stream is None:
            raise RuntimeError("GenerateRouteStreamUseCase not wired")
        async for event in self._generate_route_stream.execute(dto):
            yield event
