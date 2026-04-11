"""Application service for health-check orchestration."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from src.domain.shared.ports.service_health_port import ServiceHealthPort

logger = logging.getLogger("iaph.health")


class HealthCheckService:
    """Orchestrates health pings and caches the last-known status.

    This service lives in the Application layer and depends only on
    the ``ServiceHealthPort`` abstraction (Domain) — never on
    infrastructure or API concerns.
    """

    def __init__(
        self,
        health_port: ServiceHealthPort,
        embedding_url: str,
        llm_url: str,
        llm_provider: str,
    ) -> None:
        self._health_port = health_port
        self._embedding_url = embedding_url
        self._llm_url = llm_url
        self._llm_provider = llm_provider

        # Cached last-known status
        self._last_status: dict = {
            "embedding": {"status": "unknown", "is_cloud_run": False},
            "llm": {"status": "unknown", "is_cloud_run": False},
            "provider": "unknown",
            "last_check": None,
        }

    async def get_status(self) -> dict:
        """Ping services with short timeout and return fresh state.

        Called every ~10s by the frontend for real-time status.
        Uses a 10s timeout — if the service is cold-starting this
        will return ``"warming"`` quickly without blocking.
        """
        return await self._ping_all(timeout=10)

    async def keepalive(self) -> dict:
        """Ping services with long timeout to absorb cold starts.

        Called every ~3 min to keep Cloud Run instances alive.
        Uses a 300s timeout so the request waits for the full cold start.
        """
        return await self._ping_all(timeout=300)

    async def _ping_all(self, timeout: float) -> dict:
        """Ping all services and update cached status."""
        embedding_is_cloud_run = ".run.app" in self._embedding_url
        llm_is_cloud_run = ".run.app" in self._llm_url

        # Embedding service
        if embedding_is_cloud_run:
            embedding_status = await self._health_port.ping(
                self._embedding_url, service_type="embedding", timeout=timeout,
            )
        else:
            embedding_status = "local"

        # LLM service
        if self._llm_provider == "gemini":
            llm_status = "external"
            llm_is_cloud_run = False
        elif llm_is_cloud_run:
            llm_status = await self._health_port.ping(
                self._llm_url, service_type="llm", timeout=timeout,
            )
        else:
            llm_status = "local"

        self._last_status = {
            "embedding": {"status": embedding_status, "is_cloud_run": embedding_is_cloud_run},
            "llm": {"status": llm_status, "is_cloud_run": llm_is_cloud_run},
            "provider": self._llm_provider,
            "last_check": datetime.now(timezone.utc).isoformat(),
        }

        return self._last_status
