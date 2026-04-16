from functools import lru_cache
from urllib.parse import urlparse

from src.config import settings
from src.infrastructure.shared.auth.token_provider import (
    GcpIdentityTokenProvider,
    NullTokenProvider,
    TokenProvider,
)


def _audience_for(target_url: str) -> str:
    """Return the Cloud Run service origin (scheme://host) as the IAM audience.

    Cloud Run IAM ID-tokens are issued for an origin audience
    (e.g. ``https://uja-llm.run.app``). Including a path suffix like
    ``/v1`` in the audience causes Cloud Run to reject the token with 403.
    """
    parsed = urlparse(target_url)
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}"
    return target_url


@lru_cache(maxsize=4)
def build_token_provider(target_url: str) -> TokenProvider:
    """Return a GCP identity-token provider for Cloud Run URLs, else a no-op.

    Cached so the same URL always returns the same provider instance,
    preserving the token cache across requests.
    """
    if ".run.app" in target_url:
        return GcpIdentityTokenProvider(
            target_audience=_audience_for(target_url),
            service_account_json=settings.gcp_service_account_json,
        )
    return NullTokenProvider()
