import logging
import time

from src.config import settings
from src.domain.rag.entities.retrieved_chunk import RetrievedChunk
from src.domain.rag.ports.llm_port import LLMPort
from src.infrastructure.shared.exceptions import LLMUnavailableError
from src.infrastructure.shared.http.httpx_client import post_json

logger = logging.getLogger("iaph.llm")

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiRAGAdapter(LLMPort):
    """Calls Google Gemini API for RAG text generation."""

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

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        context_chunks: list[RetrievedChunk],
    ) -> str:
        logger.info(
            "Gemini RAG request: model=%s, max_tokens=%d, prompt=%d chars, "
            "chunks=%d",
            self._model_name,
            self._max_tokens,
            len(user_prompt),
            len(context_chunks),
        )

        logger.debug("Gemini RAG system_prompt:\n%s", system_prompt)
        logger.debug("Gemini RAG user_prompt:\n%s", user_prompt)

        payload = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"parts": [{"text": user_prompt}]}],
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
            service_label="gemini.rag",
            timeout=120.0,
            error_class=LLMUnavailableError,
        )
        latency = time.perf_counter() - t0
        content = (
            data["candidates"][0]["content"]["parts"][0]["text"]
        )
        logger.info("Gemini RAG response: %d chars, latency=%.2fs", len(content), latency)
        logger.debug("Gemini RAG full response:\n%s", content)
        return content
