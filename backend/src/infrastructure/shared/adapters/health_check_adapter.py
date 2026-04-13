"""Infrastructure adapter for pinging Cloud Run service health endpoints."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

import httpx

from src.domain.shared.ports.service_health_port import ServiceHealthPort

if TYPE_CHECKING:
    from src.infrastructure.shared.auth.token_provider import TokenProvider

logger = logging.getLogger("iaph.infra.health_check")

# Inference probe timeout — if a trivial inference responds within this,
# the model is genuinely ready (not just HTTP server up).
_PROBE_TIMEOUT = 15.0


class CloudRunHealthAdapter(ServiceHealthPort):
    """Ping Cloud Run services using IAM-authenticated HTTP requests.

    Cloud Run buffers requests during cold start and delivers them to
    the container as soon as the HTTP server starts — BEFORE the model
    engine finishes loading weights / warming KV cache.  All metadata
    endpoints (/health, /load, /v1/models) therefore return 200
    prematurely and cannot be used for readiness detection.

    The only reliable signal is a **lightweight inference probe**: a
    trivial request to the actual inference endpoint that succeeds
    quickly (<{_PROBE_TIMEOUT}s) only when the model is fully loaded.
    """

    def __init__(self, token_provider_factory) -> None:  # noqa: ANN001
        self._token_provider_factory = token_provider_factory

    async def ping(
        self, service_url: str, service_type: str, *, timeout: float = 300,
    ) -> str:
        """Ping a Cloud Run service and verify real inference readiness.

        Returns ``"ok"``, ``"warming"``, or ``"down"``.
        """
        token_provider: TokenProvider = self._token_provider_factory(service_url)
        token = await token_provider.get_token()

        headers: dict[str, str] = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                if service_type == "llm":
                    return await self._probe_llm(client, service_url, headers)
                return await self._probe_embedding(client, service_url, headers)
        except (httpx.TimeoutException, httpx.ConnectError):
            return "warming"
        except httpx.HTTPError:
            return "down"

    async def _probe_llm(
        self, client: httpx.AsyncClient, service_url: str, headers: dict,
    ) -> str:
        """Send a trivial chat completion (max_tokens=1) to verify LLM readiness."""
        url = service_url.rstrip("/")
        if not url.endswith("/v1"):
            url += "/v1"
        url += "/chat/completions"

        payload = {
            "model": "agustim/ALIA-40b-GPTQ-INT4",
            "messages": [{"role": "user", "content": "ok"}],
            "max_tokens": 1,
            "temperature": 0,
        }

        t0 = time.monotonic()
        try:
            response = await client.post(url, json=payload, headers=headers)
            elapsed = time.monotonic() - t0
            if response.status_code == 200:
                if elapsed > 10.0:
                    logger.info("LLM probe: 200 but %.1fs (Cloud Run buffered, not ready)", elapsed)
                    return "warming"
                logger.info("LLM probe ok: %.1fs", elapsed)
                return "ok"
            logger.info("LLM probe: HTTP %d (%.1fs)", response.status_code, elapsed)
            return "warming"
        except httpx.TimeoutException:
            elapsed = time.monotonic() - t0
            logger.info("LLM probe timeout after %.1fs (model loading)", elapsed)
            return "warming"

    async def _probe_embedding(
        self, client: httpx.AsyncClient, service_url: str, headers: dict,
    ) -> str:
        """Send a trivial embed request to verify embedding readiness."""
        url = service_url.rstrip("/") + "/embed"

        payload = {"texts": ["test"]}

        t0 = time.monotonic()
        try:
            response = await client.post(url, json=payload, headers=headers)
            elapsed = time.monotonic() - t0
            if response.status_code == 200:
                if elapsed > 10.0:
                    logger.info("Embedding probe: 200 but %.1fs (Cloud Run buffered, not ready)", elapsed)
                    return "warming"
                logger.info("Embedding probe ok: %.1fs", elapsed)
                return "ok"
            logger.info("Embedding probe: HTTP %d (%.1fs)", response.status_code, elapsed)
            return "warming"
        except httpx.TimeoutException:
            elapsed = time.monotonic() - t0
            logger.info("Embedding probe timeout after %.1fs (model loading)", elapsed)
            return "warming"


# Backwards-compatible free function for any existing callers.
async def ping_cloud_run_service(service_url: str, service_type: str = "embedding") -> str:  # noqa: D401
    """Legacy wrapper — prefer ``CloudRunHealthAdapter`` via composition."""
    from src.composition.token_provider_composition import build_token_provider

    adapter = CloudRunHealthAdapter(token_provider_factory=build_token_provider)
    return await adapter.ping(service_url, service_type)
