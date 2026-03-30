from src.config import settings
from src.infrastructure.shared.auth.token_provider import (
    GcpIdentityTokenProvider,
    NullTokenProvider,
    TokenProvider,
)


def build_token_provider(target_url: str) -> TokenProvider:
    """Return a GCP identity-token provider for Cloud Run URLs, else a no-op."""
    if ".run.app" in target_url:
        return GcpIdentityTokenProvider(
            target_audience=target_url,
            service_account_json=settings.gcp_service_account_json,
        )
    return NullTokenProvider()
