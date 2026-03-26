import logging

import httpx

from src.config import settings
from src.domain.chat.ports.llm_port import ConversationalLLMPort

logger = logging.getLogger("iaph.llm")


class ConversationalLLMAdapter(ConversationalLLMPort):
    """Calls vLLM for conversational (non-RAG) responses."""

    def __init__(
        self,
        base_url: str | None = None,
        model_name: str | None = None,
        max_tokens: int = 128,
        temperature: float = 0.3,
    ) -> None:
        self._base_url = base_url or settings.llm_service_url
        self._model_name = model_name or settings.llm_model_name
        self._max_tokens = max_tokens
        self._temperature = temperature

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

        headers = {}
        if settings.llm_api_key:
            headers["Authorization"] = f"Bearer {settings.llm_api_key}"
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self._base_url}/chat/completions",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            logger.info("Conversational LLM response: %d chars", len(content))
            logger.debug("Conversational LLM full response:\n%s", content)
            return content
