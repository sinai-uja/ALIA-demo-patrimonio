"""Integration tests for auth API endpoints."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.v1.endpoints.auth.deps import get_auth_service, get_current_user
from src.application.auth.dto.auth_dto import TokenPairDTO, UserInfoDTO
from src.application.auth.exceptions import InvalidCredentialsError
from src.domain.auth.entities.user import User, UserProfileType
from src.main import app

_FAKE_USER = User(
    id=uuid.uuid4(),
    username="testuser",
    password_hash="hashed",
    profile_type=UserProfileType(id=uuid.uuid4(), name="investigador"),
)


def _token_pair() -> TokenPairDTO:
    return TokenPairDTO(
        access_token="access-tok",
        refresh_token="refresh-tok",
        token_type="bearer",
    )


@pytest.fixture
def mock_auth_service():
    svc = AsyncMock()
    # get_user_info is a sync method in the real service
    svc.get_user_info = MagicMock()
    return svc


@pytest.fixture
def client(mock_auth_service):
    app.dependency_overrides[get_auth_service] = lambda: mock_auth_service
    app.dependency_overrides[get_current_user] = lambda: _FAKE_USER
    yield AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    )
    app.dependency_overrides.clear()


class TestAuthEndpoints:
    async def test_login_returns_200(self, client, mock_auth_service):
        mock_auth_service.login.return_value = _token_pair()
        resp = await client.post(
            "/api/v1/auth/login",
            json={"username": "user", "password": "pass"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["access_token"] == "access-tok"
        assert body["refresh_token"] == "refresh-tok"
        assert body["token_type"] == "bearer"

    async def test_login_invalid_credentials_returns_401(
        self, client, mock_auth_service
    ):
        mock_auth_service.login.side_effect = InvalidCredentialsError(
            "Invalid username or password"
        )
        resp = await client.post(
            "/api/v1/auth/login",
            json={"username": "bad", "password": "wrong"},
        )
        assert resp.status_code == 401
        assert "Invalid username or password" in resp.json()["detail"]

    async def test_login_missing_fields_returns_422(self, client, mock_auth_service):
        resp = await client.post("/api/v1/auth/login", json={})
        assert resp.status_code == 422

    async def test_refresh_returns_200(self, client, mock_auth_service):
        mock_auth_service.refresh.return_value = _token_pair()
        resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "old-refresh-tok"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["access_token"] == "access-tok"

    async def test_get_me_returns_200(self, client, mock_auth_service):
        mock_auth_service.get_user_info.return_value = UserInfoDTO(
            id=str(_FAKE_USER.id),
            username="testuser",
            profile_type="investigador",
        )
        resp = await client.get("/api/v1/auth/me")
        assert resp.status_code == 200
        body = resp.json()
        assert body["username"] == "testuser"
        assert body["profile_type"] == "investigador"

    async def test_list_profile_types_returns_200(self, client, mock_auth_service):
        mock_auth_service.list_profile_types.return_value = [
            "investigador",
            "ciudadano",
            "admin",
        ]
        resp = await client.get("/api/v1/auth/profile-types")
        assert resp.status_code == 200
        body = resp.json()
        # "admin" should be filtered out by the endpoint
        names = [pt["name"] for pt in body]
        assert "admin" not in names
        assert "investigador" in names
        assert "ciudadano" in names
