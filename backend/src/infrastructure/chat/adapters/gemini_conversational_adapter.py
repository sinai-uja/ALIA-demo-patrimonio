import logging
import time

from src.application.shared.exceptions import LLMUnavailableError
from src.config import settings
from src.domain.chat.ports.llm_port import ConversationalLLMPort
from src.infrastructure.shared.http.httpx_client import post_json

logger = logging.getLogger("iaph.chat.llm")

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiConversationalAdapter(ConversationalLLMPort):
    """Calls Google Gemini API for conversational responses."""

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str | None = None,
        max_tokens: int = 128,
        temperature: float = 0.3,
    ) -> None:
        self._api_key = api_key or settings.gemini_api_key
        self._model_name = model_name or settings.gemini_model_name
        self._max_tokens = max_tokens
        self._temperature = temperature

    async def generate(
        self, system_prompt: str, user_message: str,
    ) -> str:
        logger.info(
            "Gemini conversational request: model=%s, message=%d chars",
            self._model_name,
            len(user_message),
        )

        logger.debug("Gemini conversational system_prompt:\n%s", system_prompt)
        logger.debug("Gemini conversational user_message:\n%s", user_message)

        payload = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"parts": [{"text": user_message}]}],
            "generationConfig": {
                "maxOutputTokens": self._max_tokens,
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
            service_label="gemini.chat",
            timeout=60.0,
            error_class=LLMUnavailableError,
        )
        latency = time.perf_counter() - t0
        content = (
            data["candidates"][0]["content"]["parts"][0]["text"]
        )
        logger.info(
            "Gemini conversational response: %d chars, latency=%.2fs",
            len(content), latency,
        )
        logger.debug("Gemini conversational full response:\n%s", content)
        return content
