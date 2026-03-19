from src.application.search.services.search_application_service import (
    SearchApplicationService,
)
from src.domain.routes.ports.entity_detection_port import (
    EntityDetectionPort,
)
from src.domain.routes.value_objects.detected_entity import (
    DetectedEntityResult,
)


class InProcessEntityDetectionAdapter(EntityDetectionPort):
    def __init__(
        self, search_service: SearchApplicationService,
    ) -> None:
        self._search_service = search_service

    async def detect_entities(
        self, query: str,
    ) -> list[DetectedEntityResult]:
        result = await self._search_service.get_suggestions(query)
        return [
            DetectedEntityResult(
                entity_type=e.entity_type,
                value=e.value,
                display_label=e.display_label,
                matched_text=e.matched_text,
            )
            for e in result.detected_entities
        ]
