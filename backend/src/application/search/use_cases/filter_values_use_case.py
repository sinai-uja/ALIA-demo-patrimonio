import logging

from src.application.search.dto.search_dto import FilterValuesDTO
from src.domain.search.ports.filter_metadata_port import FilterMetadataPort

logger = logging.getLogger("iaph.search.filter_values")


class FilterValuesUseCase:
    """Returns available filter values for search facets."""

    def __init__(
        self, filter_metadata_port: FilterMetadataPort,
    ) -> None:
        self._filter_metadata_port = filter_metadata_port

    async def execute(
        self, provinces: list[str] | None = None,
    ) -> FilterValuesDTO:
        heritage_types = (
            await self._filter_metadata_port.get_distinct_heritage_types()
        )
        all_provinces = (
            await self._filter_metadata_port.get_distinct_provinces()
        )
        municipalities = (
            await self._filter_metadata_port.get_distinct_municipalities(
                provinces=provinces,
            )
        )

        logger.info(
            "Filter values: %d types, %d provinces, %d municipalities"
            " (provinces=%s)",
            len(heritage_types),
            len(all_provinces),
            len(municipalities),
            provinces,
        )

        return FilterValuesDTO(
            heritage_types=heritage_types,
            provinces=all_provinces,
            municipalities=municipalities,
        )
