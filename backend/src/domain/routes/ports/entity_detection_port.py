from abc import ABC, abstractmethod

from src.domain.routes.value_objects.detected_entity import (
    DetectedEntityResult,
)


class EntityDetectionPort(ABC):
    @abstractmethod
    async def detect_entities(
        self, query: str,
    ) -> list[DetectedEntityResult]: ...
