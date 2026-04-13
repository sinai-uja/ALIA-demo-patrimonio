"""Health-check endpoints for Cloud Run service monitoring.

GET  /health/services  — returns cached last-known state (lightweight, for polling)
POST /health/keepalive — pings Cloud Run services and returns fresh state (keepalive)
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.api.v1.endpoints.auth.deps import get_current_user
from src.composition.health_composition import build_health_check_service
from src.domain.auth.entities.user import User

logger = logging.getLogger("iaph.health")


# ── Response schemas ──────────────────────────────────────────────────────────

class ServiceInfo(BaseModel):
    status: str  # "ok" | "warming" | "down" | "local" | "external" | "unknown"
    is_cloud_run: bool


class HealthStatusResponse(BaseModel):
    embedding: ServiceInfo
    llm: ServiceInfo
    provider: str
    last_check: str | None = None


# ── Router ────────────────────────────────────────────────────────────────────

router = APIRouter()

_service = build_health_check_service()


@router.get("/services", response_model=HealthStatusResponse)
async def get_services_status(
    _current_user: User = Depends(get_current_user),
) -> HealthStatusResponse:
    """Return cached last-known service state (no network calls)."""
    logger.info("GET /health/services by user=%s", _current_user.username)
    data = await _service.get_status()
    return HealthStatusResponse(**data)


@router.post("/keepalive", response_model=HealthStatusResponse)
async def keepalive(
    _current_user: User = Depends(get_current_user),
) -> HealthStatusResponse:
    """Ping Cloud Run services and return fresh state."""
    logger.info("POST /health/keepalive by user=%s", _current_user.username)
    data = await _service.keepalive()
    return HealthStatusResponse(**data)
