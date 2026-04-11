"""Infrastructure adapter for pinging Cloud Run service health endpoints."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import httpx

from src.domain.shared.ports.service_health_port import ServiceHealthPort

if TYPE_CHECKING:
    from src.infrastructure.shared.auth.token_provider import TokenProvider

logger = logging.getLogger("iaph.infra.health_check")


def _build_health_url(service_url: str) -> str:
    """Strip trailing /v1 suffix and append /health."""
    url = service_url.rstrip("/")
    if url.endswith("/v1"):
        url = url[:-3]
    return f"{url}/health"


class CloudRunHealthAdapter(ServiceHealthPort):
    """Ping Cloud Run services using IAM-authenticated HTTP requests."""

    def __init__(self, token_provider_factory) -> None:  # noqa: ANN001
        """Initialise with a callable ``(url) -> TokenProvider``."""
        self._token_provider_factory = token_provider_factory

    async def ping(self, service_url: str, service_type: str, *, timeout: float = 300) -> str:
        """Ping a Cloud Run service health endpoint and verify model readiness.

        Returns one of: ``"ok"``, ``"warming"``, ``"down"``.

        - For embedding: checks that ``embedding_dim`` is not null (model loaded).
        - For LLM (vLLM): checks ``/v1/models`` endpoint for loaded models.
        """
        token_provider: TokenProvider = self._token_provider_factory(service_url)
        token = await token_provider.get_token()

        headers: dict[str, str] = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                if service_type == "llm":
                    # vLLM: check /v1/models — returns loaded models only when ready
                    models_url = service_url.rstrip("/")
                    if not models_url.endswith("/v1"):
                        models_url += "/v1"
                    models_url += "/models"
                    response = await client.get(models_url, headers=headers)
                    if response.status_code == 200:
                        data = response.json()
                        models = data.get("data", [])
                        if models:
                            return "ok"
                        logger.info("LLM health: server up but no models loaded yet")
                        return "warming"
                    logger.warning("LLM health %s returned status %d", models_url, response.status_code)
                    return "down"
                else:
                    # Embedding: check /health and verify embedding_dim is present
                    health_url = _build_health_url(service_url)
                    response = await client.get(health_url, headers=headers)
                    if response.status_code == 200:
                        data = response.json()
                        if data.get("embedding_dim") is not None:
                            return "ok"
                        logger.info("Embedding health: server up but model not loaded yet")
                        return "warming"
                    logger.warning("Embedding health %s returned status %d", health_url, response.status_code)
                    return "down"
        except (httpx.TimeoutException, httpx.ConnectError):
            return "warming"
        except httpx.HTTPError:
            return "down"


# Backwards-compatible free function for any existing callers.
async def ping_cloud_run_service(service_url: str, service_type: str = "embedding") -> str:  # noqa: D401
    """Legacy wrapper — prefer ``CloudRunHealthAdapter`` via composition."""
    from src.composition.token_provider_composition import build_token_provider

    adapter = CloudRunHealthAdapter(token_provider_factory=build_token_provider)
    return await adapter.ping(service_url, service_type)
