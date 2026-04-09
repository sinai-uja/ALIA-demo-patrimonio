from __future__ import annotations

import logging
import time

import httpx

from src.config import settings
from src.domain.rag.entities.retrieved_chunk import RetrievedChunk
from src.domain.rag.ports.llm_port import LLMPort
from src.infrastructure.shared.auth.token_provider import TokenProvider
from src.application.shared.exceptions import LLMUnavailableError
from src.infrastructure.shared.http.httpx_client import post_json

logger = logging.getLogger("iaph.rag.llm")

_SERVICE_LABEL = "vllm.rag"


class VLLMAdapter(LLMPort):
    """Calls a vLLM-compatible OpenAI chat completions endpoint."""

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
        self._temperature = (
            temperature if temperature is not None else settings.llm_temperature
        )
        self._token_provider = token_provider

    async def _build_auth_headers(self) -> dict[str, str]:
        if self._token_provider:
            token = await self._token_provider.get_token()
            if token:
                return {"Authorization": f"Bearer {token}"}
        if settings.llm_api_key:
            return {"Authorization": f"Bearer {settings.llm_api_key}"}
        return {}

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        context_chunks: list[RetrievedChunk],
    ) -> str:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        logger.info(
            "LLM request: model=%s, max_tokens=%d, prompt=%d chars, chunks=%d",
            self._model_name, self._max_tokens, len(user_prompt), len(context_chunks),
        )
        logger.debug("LLM system_prompt:\n%s", system_prompt)
        logger.debug("LLM user_prompt:\n%s", user_prompt)

        payload = {
            "model": self._model_name,
            "messages": messages,
            "max_tokens": self._max_tokens,
            "temperature": self._temperature,
        }

        headers = await self._build_auth_headers()
        url = f"{self._base_url}/chat/completions"

        t0 = time.perf_counter()
        try:
            data = await post_json(
                url,
                payload,
                service_label=_SERVICE_LABEL,
                timeout=120.0,
                headers=headers or None,
                error_class=LLMUnavailableError,
            )
        except LLMUnavailableError as exc:
            # Preserve the legacy 400-halving-max-tokens retry semantic: the
            # shared helper raises ``LLMUnavailableError`` with the original
            # ``httpx.HTTPStatusError`` chained via ``__cause__``. If the
            # first attempt failed with HTTP 400, halve ``max_tokens`` and
            # retry once through the same helper; any other failure
            # propagates unchanged.
            cause = exc.__cause__
            if (
                isinstance(cause, httpx.HTTPStatusError)
                and cause.response.status_code == 400
            ):
                try:
                    body = cause.response.json()
                    error_msg = body.get("message", str(body))
                except Exception:  # noqa: BLE001 - defensive body parsing
                    error_msg = cause.response.text[:500]
                logger.warning("LLM 400 error: %s", error_msg)
                reduced = max(64, self._max_tokens // 2)
                payload["max_tokens"] = reduced
                logger.info("Retrying with max_tokens=%d", reduced)
                data = await post_json(
                    url,
                    payload,
                    service_label=_SERVICE_LABEL,
                    timeout=120.0,
                    headers=headers or None,
                    error_class=LLMUnavailableError,
                )
            else:
                raise
        latency = time.perf_counter() - t0

        content = data["choices"][0]["message"]["content"]
        logger.info("LLM response: %d chars, latency=%.2fs", len(content), latency)
        logger.debug("LLM full response:\n%s", content)
        return content
