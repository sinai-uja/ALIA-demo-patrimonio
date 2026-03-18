import logging
import time

from src.application.search.dto.search_dto import (
    DetectedEntityDTO,
    SuggestionResponseDTO,
)
from src.domain.search.ports.filter_metadata_port import FilterMetadataPort
from src.domain.search.services.entity_detection_service import (
    EntityDetectionService,
)

logger = logging.getLogger("iaph.search")

CACHE_TTL_SECONDS = 300  # 5 minutes


class SuggestionUseCase:
    """Detects entities in a search query and returns suggestions."""

    def __init__(
        self,
        filter_metadata_port: FilterMetadataPort,
        entity_detection_service: EntityDetectionService,
    ) -> None:
        self._filter_metadata_port = filter_metadata_port
        self._entity_detection_service = entity_detection_service
        self._cache: dict[str, tuple[float, list[str]]] = {}

    async def _get_cached(
        self, key: str, fetcher: object,
    ) -> list[str]:
        """Retrieve values from cache or fetch and cache them."""
        now = time.monotonic()
        if key in self._cache:
            ts, values = self._cache[key]
            if now - ts < CACHE_TTL_SECONDS:
                return values
        values = await fetcher()  # type: ignore[operator]
        self._cache[key] = (now, values)
        return values

    async def execute(self, query: str) -> SuggestionResponseDTO:
        provinces = await self._get_cached(
            "provinces",
            self._filter_metadata_port.get_distinct_provinces,
        )
        municipalities = await self._get_cached(
            "municipalities",
            self._filter_metadata_port.get_distinct_municipalities,
        )
        heritage_types = await self._get_cached(
            "heritage_types",
            self._filter_metadata_port.get_distinct_heritage_types,
        )

        detected = self._entity_detection_service.detect(
            query=query,
            provinces=provinces,
            municipalities=municipalities,
            heritage_types=heritage_types,
        )

        entity_dtos = [
            DetectedEntityDTO(
                entity_type=e.entity_type,
                value=e.value,
                display_label=e.display_label,
                matched_text=e.matched_text,
            )
            for e in detected
        ]

        # Build a search label from detected entities
        if entity_dtos:
            labels = [e.display_label for e in entity_dtos]
            search_label = f"Buscar: {query} ({', '.join(labels)})"
        else:
            search_label = f"Buscar: {query}"

        logger.info(
            "Suggestions for query=%r: %d entities detected",
            query[:80],
            len(entity_dtos),
        )

        return SuggestionResponseDTO(
            query=query,
            search_label=search_label,
            detected_entities=entity_dtos,
        )
