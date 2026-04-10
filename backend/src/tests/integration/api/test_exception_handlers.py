"""Tests for global FastAPI exception handlers.

Creates a minimal FastAPI app with the exception handlers registered,
then verifies each mapped exception produces the correct HTTP response.
"""

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.api.v1.exception_handlers import register_exception_handlers
from src.application.auth.exceptions import InvalidCredentialsError, InvalidTokenError
from src.application.shared.exceptions import (
    ApplicationError,
    ConflictError,
    ExternalServiceUnavailableError,
    LLMResponseParseError,
    ResourceNotFoundError,
    UnauthorizedActionError,
    ValidationError,
)


def _build_app() -> FastAPI:
    """Build a minimal FastAPI app with exception-raising endpoints."""
    test_app = FastAPI()
    register_exception_handlers(test_app)

    @test_app.get("/raise/resource-not-found")
    async def _raise_not_found():
        raise ResourceNotFoundError("thing not found")

    @test_app.get("/raise/conflict")
    async def _raise_conflict():
        raise ConflictError("already exists")

    @test_app.get("/raise/unauthorized-action")
    async def _raise_unauthorized():
        raise UnauthorizedActionError("forbidden")

    @test_app.get("/raise/validation")
    async def _raise_validation():
        raise ValidationError("bad input")

    @test_app.get("/raise/external-unavailable")
    async def _raise_external():
        raise ExternalServiceUnavailableError("service down")

    @test_app.get("/raise/llm-parse")
    async def _raise_llm_parse():
        raise LLMResponseParseError("bad llm output")

    @test_app.get("/raise/invalid-credentials")
    async def _raise_invalid_creds():
        raise InvalidCredentialsError("wrong password")

    @test_app.get("/raise/invalid-token")
    async def _raise_invalid_token():
        raise InvalidTokenError("token expired")

    @test_app.get("/raise/application-error")
    async def _raise_app_error():
        raise ApplicationError("generic app error")

    return test_app


_test_app = _build_app()


@pytest.fixture
def client():
    return AsyncClient(
        transport=ASGITransport(app=_test_app), base_url="http://test"
    )


class TestExceptionHandlers:
    async def test_resource_not_found_returns_404(self, client):
        resp = await client.get("/raise/resource-not-found")
        assert resp.status_code == 404
        assert resp.json() == {"detail": "thing not found"}

    async def test_conflict_returns_409(self, client):
        resp = await client.get("/raise/conflict")
        assert resp.status_code == 409
        assert resp.json() == {"detail": "already exists"}

    async def test_unauthorized_action_returns_403(self, client):
        resp = await client.get("/raise/unauthorized-action")
        assert resp.status_code == 403
        assert resp.json() == {"detail": "forbidden"}

    async def test_validation_returns_422(self, client):
        resp = await client.get("/raise/validation")
        assert resp.status_code == 422
        assert resp.json() == {"detail": "bad input"}

    async def test_external_unavailable_returns_502(self, client):
        resp = await client.get("/raise/external-unavailable")
        assert resp.status_code == 502
        assert resp.json() == {"detail": "service down"}

    async def test_llm_parse_error_returns_502(self, client):
        resp = await client.get("/raise/llm-parse")
        assert resp.status_code == 502
        assert resp.json() == {"detail": "bad llm output"}

    async def test_invalid_credentials_returns_401_with_www_authenticate(self, client):
        resp = await client.get("/raise/invalid-credentials")
        assert resp.status_code == 401
        assert resp.json() == {"detail": "wrong password"}
        assert resp.headers["www-authenticate"] == "Bearer"

    async def test_invalid_token_returns_401_with_www_authenticate(self, client):
        resp = await client.get("/raise/invalid-token")
        assert resp.status_code == 401
        assert resp.json() == {"detail": "token expired"}
        assert resp.headers["www-authenticate"] == "Bearer"

    async def test_application_error_fallback_returns_400(self, client):
        resp = await client.get("/raise/application-error")
        assert resp.status_code == 400
        assert resp.json() == {"detail": "generic app error"}
