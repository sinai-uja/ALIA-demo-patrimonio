from abc import ABC, abstractmethod

from src.domain.accessibility.value_objects.simplification_level import SimplificationLevel


class LLMPort(ABC):
    """Port for LLM text simplification in the accessibility context."""

    @abstractmethod
    async def simplify(self, text: str, level: SimplificationLevel) -> str:
        ...
