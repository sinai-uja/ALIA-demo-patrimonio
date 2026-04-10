"""Tests for VLLMAdapter — HTTP mocking with respx.

The adapter calls ``post_json`` which creates a new ``httpx.AsyncClient``
per request. We use ``respx`` to intercept outbound calls to the
configured chat completions URL.
"""

import httpx
import pytest
import respx

from src.application.shared.exceptions import LLMUnavailableError
from src.infrastructure.rag.adapters.llm_adapter import VLLMAdapter

BASE_URL = "https://llm.test.local/v1"
COMPLETIONS_URL = f"{BASE_URL}/chat/completions"


def _ok_response(content: str = "The answer is 42.") -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "choices": [
                {"message": {"content": content}, "finish_reason": "stop"}
            ]
        },
    )


@pytest.fixture
def adapter() -> VLLMAdapter:
    return VLLMAdapter(
        base_url=BASE_URL,
        model_name="test-model",
        max_tokens=512,
        temperature=0.0,
        token_provider=None,
    )


class TestGenerateSuccess:
    @respx.mock
    async def test_200_returns_parsed_content(self, adapter: VLLMAdapter):
        respx.post(COMPLETIONS_URL).mock(return_value=_ok_response("Hello world"))
        result = await adapter.generate(
            system_prompt="You are helpful.",
            user_prompt="Say hello.",
            context_chunks=[],
        )
        assert result == "Hello world"


class TestGenerateRetryOn400:
    @respx.mock
    async def test_400_retries_with_halved_max_tokens_and_succeeds(
        self, adapter: VLLMAdapter
    ):
        """First call returns 400, second call with halved max_tokens returns 200."""
        call_count = 0

        def side_effect(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # Simulate 400 error (e.g. context too long)
                resp = httpx.Response(
                    400,
                    json={"message": "max_tokens too large"},
                    request=request,
                )
                return resp
            return _ok_response("Retried successfully")

        respx.post(COMPLETIONS_URL).mock(side_effect=side_effect)
        result = await adapter.generate(
            system_prompt="System",
            user_prompt="User",
            context_chunks=[],
        )
        assert result == "Retried successfully"
        assert call_count == 2


class TestGenerateErrors:
    @respx.mock
    async def test_500_raises_llm_unavailable(self, adapter: VLLMAdapter):
        respx.post(COMPLETIONS_URL).mock(
            return_value=httpx.Response(500, json={"error": "internal"})
        )
        with pytest.raises(LLMUnavailableError):
            await adapter.generate(
                system_prompt="System",
                user_prompt="User",
                context_chunks=[],
            )

    @respx.mock
    async def test_connection_timeout_raises_llm_unavailable(self, adapter: VLLMAdapter):
        respx.post(COMPLETIONS_URL).mock(side_effect=httpx.ConnectTimeout("timeout"))
        with pytest.raises(LLMUnavailableError):
            await adapter.generate(
                system_prompt="System",
                user_prompt="User",
                context_chunks=[],
            )

    @respx.mock
    async def test_both_attempts_fail_raises_llm_unavailable(self, adapter: VLLMAdapter):
        """400 on first attempt, then 500 on retry -> LLMUnavailableError."""
        call_count = 0

        def side_effect(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return httpx.Response(
                    400,
                    json={"message": "too large"},
                    request=request,
                )
            return httpx.Response(500, json={"error": "down"})

        respx.post(COMPLETIONS_URL).mock(side_effect=side_effect)
        with pytest.raises(LLMUnavailableError):
            await adapter.generate(
                system_prompt="System",
                user_prompt="User",
                context_chunks=[],
            )
        assert call_count == 2
