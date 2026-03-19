from src.application.routes.dto.routes_dto import (
    DetectedEntityDTO,
    RouteSuggestionResponseDTO,
)
from src.domain.routes.ports.entity_detection_port import (
    EntityDetectionPort,
)


class RouteSuggestionsUseCase:
    def __init__(
        self, entity_detection_port: EntityDetectionPort,
    ) -> None:
        self._entity_detection_port = entity_detection_port

    async def execute(
        self, query: str,
    ) -> RouteSuggestionResponseDTO:
        detected = await self._entity_detection_port.detect_entities(
            query,
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
        if entity_dtos:
            labels = [e.display_label for e in entity_dtos]
            search_label = (
                f"Planificar ruta: {query} "
                f"({', '.join(labels)})"
            )
        else:
            search_label = f"Planificar ruta: {query}"

        return RouteSuggestionResponseDTO(
            query=query,
            search_label=search_label,
            detected_entities=entity_dtos,
        )
