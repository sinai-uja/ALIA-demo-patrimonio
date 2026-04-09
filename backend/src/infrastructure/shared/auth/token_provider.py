from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Protocol

logger = logging.getLogger("iaph.auth.token_provider")


class TokenProvider(Protocol):
    """Provides authentication tokens for inter-service communication."""

    async def get_token(self) -> str | None: ...


class NullTokenProvider:
    """No-op provider for local/Docker environments where no IAM token is needed."""

    async def get_token(self) -> str | None:
        return None


class GcpIdentityTokenProvider:
    """Fetches GCP identity tokens for Cloud Run IAM authentication.

    Supports two credential sources (in order of priority):
      1. Service account JSON string (for non-GCP servers, via GCP_SERVICE_ACCOUNT_JSON)
      2. Default credentials: metadata server (Cloud Run/GCE) or ADC (local dev)

    Tokens are cached and refreshed 5 minutes before expiry (1h lifetime).
    The google-auth library is imported lazily so this module can be safely
    imported even when google-auth is not installed.
    """

    def __init__(self, target_audience: str, service_account_json: str = "") -> None:
        self._target_audience = target_audience
        self._service_account_json = service_account_json
        self._credentials = None
        self._cached_token: str | None = None
        self._expiry: float = 0.0

    async def get_token(self) -> str | None:
        if self._cached_token and time.time() < self._expiry - 300:
            return self._cached_token
        try:
            token = await asyncio.to_thread(self._fetch_token)
        except ImportError:
            logger.warning(
                "google-auth not installed — cannot obtain identity token for %s. "
                "Install with: uv pip install google-auth",
                self._target_audience,
            )
            return None
        self._cached_token = token
        self._expiry = time.time() + 3600
        return token

    def _fetch_token(self) -> str:
        from google.auth.transport.requests import Request

        if self._service_account_json:
            return self._fetch_with_service_account(Request())
        return self._fetch_with_default_credentials(Request())

    def _fetch_with_service_account(self, request) -> str:
        from google.oauth2 import service_account

        if self._credentials is None:
            info = json.loads(self._service_account_json)
            self._credentials = service_account.IDTokenCredentials.from_service_account_info(
                info, target_audience=self._target_audience
            )
        self._credentials.refresh(request)
        return self._credentials.token

    def _fetch_with_default_credentials(self, request) -> str:
        from google.oauth2 import id_token

        return id_token.fetch_id_token(request, self._target_audience)
