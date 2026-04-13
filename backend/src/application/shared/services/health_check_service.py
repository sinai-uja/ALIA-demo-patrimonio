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
        """Return cached last-known service state (no network calls).

        Called every ~10s by the frontend. Returns instantly from cache.
        The cache is updated only by ``keepalive()`` (every ~3 min).
        """
        return self._last_status

    async def keepalive(self) -> dict:
        """Ping services with long timeout to absorb cold starts.

        Called every ~3 min to keep Cloud Run instances alive.
        Uses a 300s timeout so the request waits for the full cold start.
        """
        return await self._ping_all(timeout=300)

    async def _ping_all(self, timeout: float) -> dict:
        """Ping all services and update cached status incrementally.

        Each service updates the cache as soon as its probe completes,
        so the frontend sees partial progress (e.g. embedding "ok" while
        LLM is still warming up).
        """
        embedding_is_cloud_run = ".run.app" in self._embedding_url
        llm_is_cloud_run = ".run.app" in self._llm_url

        # Reset Cloud Run services to "warming" only if the last check
        # was more than 5 minutes ago (Cloud Run scales to zero after ~10 min).
        # This avoids a false "warming" flash when services are still warm.
        last = self._last_status.get("last_check")
        stale = True
        if last:
            try:
                last_dt = datetime.fromisoformat(last)
                stale = (datetime.now(timezone.utc) - last_dt).total_seconds() > 300
            except (ValueError, TypeError):
                stale = True

        if stale:
            if embedding_is_cloud_run:
                self._last_status["embedding"] = {"status": "warming", "is_cloud_run": True}
            if llm_is_cloud_run:
                self._last_status["llm"] = {"status": "warming", "is_cloud_run": True}
        self._last_status["provider"] = self._llm_provider
        self._last_status["last_check"] = datetime.now(timezone.utc).isoformat()

        # Embedding service — update cache immediately after probe
        if embedding_is_cloud_run:
            embedding_status = await self._health_port.ping(
                self._embedding_url, service_type="embedding", timeout=timeout,
            )
        else:
            embedding_status = "local"

        self._last_status["embedding"] = {
            "status": embedding_status, "is_cloud_run": embedding_is_cloud_run,
        }
        self._last_status["last_check"] = datetime.now(timezone.utc).isoformat()

        # LLM service — update cache immediately after probe
        if self._llm_provider == "gemini":
            llm_status = "external"
            llm_is_cloud_run = False
        elif llm_is_cloud_run:
            llm_status = await self._health_port.ping(
                self._llm_url, service_type="llm", timeout=timeout,
            )
        else:
            llm_status = "local"

        self._last_status["llm"] = {
            "status": llm_status, "is_cloud_run": llm_is_cloud_run,
        }
        self._last_status["provider"] = self._llm_provider
        self._last_status["last_check"] = datetime.now(timezone.utc).isoformat()

        return self._last_status
