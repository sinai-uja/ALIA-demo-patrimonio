from src.application.routes.dto.routes_dto import RouteFilterValuesDTO
from src.domain.routes.ports.filter_metadata_port import (
    FilterMetadataPort,
)


class RouteFilterValuesUseCase:
    def __init__(
        self, filter_metadata_port: FilterMetadataPort,
    ) -> None:
        self._filter_metadata_port = filter_metadata_port

    async def execute(
        self, provinces: list[str] | None = None,
    ) -> RouteFilterValuesDTO:
        heritage_types = (
            await self._filter_metadata_port.get_distinct_heritage_types()
        )
        all_provinces = (
            await self._filter_metadata_port.get_distinct_provinces()
        )
        municipalities = (
            await self._filter_metadata_port.get_distinct_municipalities(
                provinces,
            )
        )
        return RouteFilterValuesDTO(
            heritage_types=heritage_types,
            provinces=all_provinces,
            municipalities=municipalities,
        )
