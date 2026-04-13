"""Composition root for the health-check feature."""

from src.application.shared.services.health_check_service import (
    HealthCheckService,
)
from src.composition.token_provider_composition import build_token_provider
from src.config import settings
from src.infrastructure.shared.adapters.health_check_adapter import (
    CloudRunHealthAdapter,
)


def build_health_check_service() -> HealthCheckService:
    """Wire the health-check service with its infrastructure adapter."""
    adapter = CloudRunHealthAdapter(
        token_provider_factory=build_token_provider,
    )
    return HealthCheckService(
        health_port=adapter,
        embedding_url=settings.embedding_service_url,
        llm_url=settings.llm_service_url,
        llm_provider=settings.llm_provider,
    )
