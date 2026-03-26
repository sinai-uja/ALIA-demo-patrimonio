import logging

import httpx

from src.config import settings
from src.domain.accessibility.ports.llm_port import LLMPort
from src.domain.accessibility.prompts import (
    BASIC_SYSTEM_PROMPT,
    INTERMEDIATE_SYSTEM_PROMPT,
    build_simplification_prompt,
)
from src.domain.accessibility.value_objects.simplification_level import SimplificationLevel

logger = logging.getLogger("iaph.llm")


class AccessibilityLLMAdapter(LLMPort):
    """Calls a vLLM-compatible OpenAI chat completions endpoint for text simplification."""

    def __init__(
        self,
        base_url: str | None = None,
        model_name: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.3,
    ) -> None:
        self._base_url = base_url or settings.llm_service_url
        self._model_name = model_name or settings.llm_model_name
        self._max_tokens = max_tokens
        self._temperature = temperature

    async def simplify(self, text: str, level: SimplificationLevel) -> str:
        system_prompt = (
            BASIC_SYSTEM_PROMPT
            if level == SimplificationLevel.BASIC
            else INTERMEDIATE_SYSTEM_PROMPT
        )
        user_prompt = build_simplification_prompt(text)

        logger.info(
            "Accessibility LLM request: model=%s, level=%s, text=%d chars",
            self._model_name, level.value, len(text),
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        payload = {
            "model": self._model_name,
            "messages": messages,
            "max_tokens": self._max_tokens,
            "temperature": self._temperature,
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self._base_url}/chat/completions",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            logger.info("Accessibility LLM response: %d chars", len(content))
            return content
