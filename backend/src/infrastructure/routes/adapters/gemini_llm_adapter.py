import logging
import time

from src.config import settings
from src.domain.routes.ports.llm_port import LLMPort
from src.domain.routes.value_objects.route_narrative import RouteNarrative
from src.infrastructure.routes.adapters._narrative_parser import (
    parse_narrative_json,
)
from src.infrastructure.shared.exceptions import LLMUnavailableError
from src.infrastructure.shared.http.httpx_client import post_json

logger = logging.getLogger("iaph.llm")

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiRoutesAdapter(LLMPort):
    """Calls Google Gemini API for route generation."""

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> None:
        self._api_key = api_key or settings.gemini_api_key
        self._model_name = model_name or settings.gemini_model_name
        self._max_tokens = max_tokens or settings.llm_max_tokens
        self._temperature = (
            temperature if temperature is not None else settings.llm_temperature
        )

    async def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int | None = None,
        history: list[dict[str, str]] | None = None,
    ) -> str:
        effective_max_tokens = max_tokens or self._max_tokens
        logger.info(
            "Gemini routes request: model=%s, max_tokens=%d, prompt=%d chars",
            self._model_name,
            effective_max_tokens,
            len(user_prompt),
        )

        logger.debug("Gemini routes system_prompt:\n%s", system_prompt)
        logger.debug("Gemini routes user_prompt:\n%s", user_prompt)

        contents: list[dict] = []
        if history:
            for msg in history:
                role = "model" if msg["role"] == "assistant" else "user"
                contents.append({"role": role, "parts": [{"text": msg["content"]}]})
        contents.append({"role": "user", "parts": [{"text": user_prompt}]})

        payload = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": effective_max_tokens,
                "temperature": self._temperature,
            },
        }

        url = (
            f"{GEMINI_API_URL}/{self._model_name}:generateContent"
            f"?key={self._api_key}"
        )

        t0 = time.perf_counter()
        data = await post_json(
            url,
            payload,
            service_label="gemini.routes",
            timeout=120.0,
            error_class=LLMUnavailableError,
        )
        latency = time.perf_counter() - t0
        content = (
            data["candidates"][0]["content"]["parts"][0]["text"]
        )
        logger.info(
            "Gemini routes response: %d chars, latency=%.2fs", len(content), latency,
        )
        logger.debug("Gemini routes full response:\n%s", content)
        return content

    async def generate_route_narrative(
        self,
        system_prompt: str,
        user_prompt: str,
        province_label: str,
        max_tokens: int | None = None,
    ) -> RouteNarrative:
        raw = await self.generate_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=max_tokens,
        )
        return parse_narrative_json(raw, province_label)
