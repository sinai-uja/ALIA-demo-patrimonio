"""Tests for HttpEmbeddingAdapter — HTTP mocking with respx.

The adapter calls ``post_json`` which creates a new ``httpx.AsyncClient``
per request, so we use ``respx`` in router mode to intercept all outbound
calls matching the configured base URL.
"""

import asyncio

import httpx
import pytest
import respx

from src.application.shared.exceptions import EmbeddingServiceUnavailableError
from src.infrastructure.shared.adapters.embedding_adapter import HttpEmbeddingAdapter


async def _noop_sleep(_seconds: float) -> None:
    """Replacement for asyncio.sleep that returns immediately."""
    return

BASE_URL = "https://embedding.test.local"
EMBED_URL = f"{BASE_URL}/embed"


@pytest.fixture
def adapter() -> HttpEmbeddingAdapter:
    return HttpEmbeddingAdapter(base_url=BASE_URL, token_provider=None)


class TestEmbedSuccess:
    @respx.mock
    async def test_200_returns_embedding_vectors(self, adapter: HttpEmbeddingAdapter):
        respx.post(EMBED_URL).mock(
            return_value=httpx.Response(
                200, json={"embeddings": [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]}
            )
        )
        result = await adapter.embed(["hello", "world"])
        assert len(result) == 2
        assert result[0] == [0.1, 0.2, 0.3]
        assert result[1] == [0.4, 0.5, 0.6]


class TestEmbedErrors:
    @respx.mock
    async def test_503_raises_embedding_service_unavailable(self, adapter: HttpEmbeddingAdapter):
        respx.post(EMBED_URL).mock(
            return_value=httpx.Response(503, json={"error": "overloaded"})
        )
        with pytest.raises(EmbeddingServiceUnavailableError):
            await adapter.embed(["single text"])

    @respx.mock
    async def test_connection_timeout_raises_embedding_service_unavailable(
        self, adapter: HttpEmbeddingAdapter
    ):
        respx.post(EMBED_URL).mock(side_effect=httpx.ConnectTimeout("timeout"))
        with pytest.raises(EmbeddingServiceUnavailableError):
            await adapter.embed(["single text"])


class TestEmbedBatchFallback:
    @respx.mock
    async def test_batch_fails_then_per_item_retry_succeeds(
        self, adapter: HttpEmbeddingAdapter, monkeypatch: pytest.MonkeyPatch
    ):
        """First batch call fails (500), per-item retries succeed."""
        # Eliminate the 2-second sleep for faster tests
        monkeypatch.setattr(asyncio, "sleep", _noop_sleep)

        call_count = 0

        def side_effect(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First batch call fails
                return httpx.Response(500, json={"error": "batch failed"})
            # Per-item calls succeed
            return httpx.Response(200, json={"embeddings": [[0.1, 0.2]]})

        respx.post(EMBED_URL).mock(side_effect=side_effect)
        result = await adapter.embed(["text1", "text2"])
        assert len(result) == 2
        assert call_count == 3  # 1 batch + 2 per-item

    @respx.mock
    async def test_all_calls_fail_raises_embedding_service_unavailable(
        self, adapter: HttpEmbeddingAdapter, monkeypatch: pytest.MonkeyPatch
    ):
        """When batch and all per-item calls fail, error propagates."""
        monkeypatch.setattr(asyncio, "sleep", _noop_sleep)

        # All calls return 500
        respx.post(EMBED_URL).mock(
            return_value=httpx.Response(500, json={"error": "down"})
        )
        with pytest.raises(EmbeddingServiceUnavailableError):
            await adapter.embed(["text1", "text2"])
