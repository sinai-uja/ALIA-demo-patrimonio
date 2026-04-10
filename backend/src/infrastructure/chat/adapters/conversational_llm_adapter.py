from __future__ import annotations

import logging
import time

from src.config import settings
from src.domain.chat.ports.llm_port import ConversationalLLMPort
from src.infrastructure.shared.auth.token_provider import TokenProvider
from src.application.shared.exceptions import LLMUnavailableError
from src.infrastructure.shared.http.httpx_client import post_json

logger = logging.getLogger("iaph.chat.llm")


class ConversationalLLMAdapter(ConversationalLLMPort):
    """Calls vLLM for conversational (non-RAG) responses."""

    def __init__(
        self,
        base_url: str | None = None,
        model_name: str | None = None,
        max_tokens: int = 128,
        temperature: float = 0.3,
        token_provider: TokenProvider | None = None,
    ) -> None:
        self._base_url = base_url or settings.llm_service_url
        self._model_name = model_name or settings.llm_model_name
        self._max_tokens = max_tokens
        self._temperature = temperature
        self._token_provider = token_provider

    async def _build_auth_headers(self) -> dict[str, str]:
        if self._token_provider:
            token = await self._token_provider.get_token()
            if token:
                return {"Authorization": f"Bearer {token}"}
        if settings.llm_api_key:
            return {"Authorization": f"Bearer {settings.llm_api_key}"}
        return {}

    async def generate(self, system_prompt: str, user_message: str) -> str:
        logger.info(
            "Conversational LLM request: model=%s, max_tokens=%d, message=%d chars",
            self._model_name, self._max_tokens, len(user_message),
        )
        logger.debug("Conversational LLM system_prompt:\n%s", system_prompt)
        logger.debug("Conversational LLM user_message:\n%s", user_message)

        payload = {
            "model": self._model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "max_tokens": self._max_tokens,
            "temperature": self._temperature,
        }

        headers = await self._build_auth_headers()
        t0 = time.perf_counter()
        data = await post_json(
            f"{self._base_url}/chat/completions",
            payload,
            service_label="vllm.chat",
            timeout=60.0,
            headers=headers or None,
            error_class=LLMUnavailableError,
        )
        latency = time.perf_counter() - t0
        content = data["choices"][0]["message"]["content"]
        logger.info(
            "Conversational LLM response: %d chars, latency=%.2fs", len(content), latency,
        )
        logger.debug("Conversational LLM full response:\n%s", content)
        return content
