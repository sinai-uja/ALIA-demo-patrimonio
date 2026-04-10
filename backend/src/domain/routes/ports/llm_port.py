from abc import ABC, abstractmethod

from src.domain.routes.value_objects.route_narrative import RouteNarrative


class LLMPort(ABC):
    """Port for LLM text generation within the routes context."""

    @abstractmethod
    async def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int | None = None,
        history: list[dict[str, str]] | None = None,
    ) -> str:
        """Generate free-form text from a system and user prompt pair.

        Args:
            max_tokens: Override the default max tokens for this call.
            history: Optional conversation history as a list of
                     {"role": "user"|"assistant", "content": "..."} dicts.
        """
        ...

    @abstractmethod
    async def generate_route_narrative(
        self,
        system_prompt: str,
        user_prompt: str,
        province_label: str,
        max_tokens: int | None = None,
    ) -> RouteNarrative:
        """Generate a structured route narrative.

        The adapter is responsible for invoking the LLM, parsing its
        response into a :class:`RouteNarrative` and raising
        ``LLMResponseParseError`` when parsing is impossible. The
        ``province_label`` is used to build a sensible default title when
        the LLM response lacks one.
        """
        ...
