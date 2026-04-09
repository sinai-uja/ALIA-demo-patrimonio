from __future__ import annotations

import logging
import time

from src.config import settings
from src.domain.routes.ports.llm_port import LLMPort
from src.domain.routes.value_objects.route_narrative import RouteNarrative
from src.infrastructure.routes.adapters._narrative_parser import (
    parse_narrative_json,
)
from src.infrastructure.shared.auth.token_provider import TokenProvider
from src.infrastructure.shared.exceptions import LLMUnavailableError
from src.infrastructure.shared.http.httpx_client import post_json

logger = logging.getLogger("iaph.llm")


class VLLMRoutesAdapter(LLMPort):
    """Calls a vLLM-compatible OpenAI chat completions endpoint for route generation."""

    def __init__(
        self,
        base_url: str | None = None,
        model_name: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        token_provider: TokenProvider | None = None,
    ) -> None:
        self._base_url = base_url or settings.llm_service_url
        self._model_name = model_name or settings.llm_model_name
        self._max_tokens = max_tokens or settings.llm_max_tokens
        self._temperature = temperature if temperature is not None else settings.llm_temperature
        self._token_provider = token_provider

    async def _build_auth_headers(self) -> dict[str, str]:
        if self._token_provider:
            token = await self._token_provider.get_token()
            if token:
                return {"Authorization": f"Bearer {token}"}
        if settings.llm_api_key:
            return {"Authorization": f"Bearer {settings.llm_api_key}"}
        return {}

    async def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int | None = None,
        history: list[dict[str, str]] | None = None,
    ) -> str:
        effective_max_tokens = max_tokens or self._max_tokens
        messages = [{"role": "system", "content": system_prompt}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user_prompt})

        logger.info(
            "vLLM routes request: model=%s, max_tokens=%d, prompt=%d chars",
            self._model_name, effective_max_tokens, len(user_prompt),
        )
        logger.debug("vLLM routes system_prompt:\n%s", system_prompt)
        logger.debug("vLLM routes user_prompt:\n%s", user_prompt)

        payload = {
            "model": self._model_name,
            "messages": messages,
            "max_tokens": effective_max_tokens,
            "temperature": self._temperature,
        }

        headers = await self._build_auth_headers()
        t0 = time.perf_counter()
        data = await post_json(
            f"{self._base_url}/chat/completions",
            payload,
            service_label="vllm.routes",
            timeout=120.0,
            headers=headers or None,
            error_class=LLMUnavailableError,
        )
        latency = time.perf_counter() - t0
        content = data["choices"][0]["message"]["content"]
        logger.info("vLLM routes response: %d chars, latency=%.2fs", len(content), latency)
        logger.debug("vLLM routes full response:\n%s", content)
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
