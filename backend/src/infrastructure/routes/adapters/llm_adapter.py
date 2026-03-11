import httpx

from src.config import settings
from src.domain.routes.ports.llm_port import LLMPort


class VLLMRoutesAdapter(LLMPort):
    """Calls a vLLM-compatible OpenAI chat completions endpoint for route generation."""

    def __init__(
        self,
        base_url: str | None = None,
        model_name: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> None:
        self._base_url = base_url or settings.llm_service_url
        self._model_name = model_name or settings.llm_model_name
        self._max_tokens = max_tokens or settings.llm_max_tokens
        self._temperature = temperature if temperature is not None else settings.llm_temperature

    async def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
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
            return data["choices"][0]["message"]["content"]
