from abc import ABC, abstractmethod


class LLMPort(ABC):
    """Port for structured LLM text generation within the routes context."""

    @abstractmethod
    async def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        """Generate text from a system and user prompt pair."""
        ...
