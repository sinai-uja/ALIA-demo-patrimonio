from abc import ABC, abstractmethod


class LLMPort(ABC):
    """Port for structured LLM text generation within the routes context."""

    @abstractmethod
    async def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int | None = None,
        history: list[dict[str, str]] | None = None,
    ) -> str:
        """Generate text from a system and user prompt pair.

        Args:
            max_tokens: Override the default max tokens for this call.
            history: Optional conversation history as a list of
                     {"role": "user"|"assistant", "content": "..."} dicts.
        """
        ...
