"""Tests for JWTTokenAdapter — pure unit tests (no HTTP, no DB).

The adapter is a synchronous, pure-Python implementation of TokenPort.
We verify token creation and validation logic directly.
"""

from datetime import UTC, datetime, timedelta

import jwt
import pytest

from src.infrastructure.auth.adapters.jwt_token_adapter import JWTTokenAdapter

SECRET = "test-secret-key-for-unit-tests"
ALGORITHM = "HS256"
ACCESS_MINUTES = 15
REFRESH_DAYS = 7


@pytest.fixture
def adapter() -> JWTTokenAdapter:
    return JWTTokenAdapter(
        secret_key=SECRET,
        algorithm=ALGORITHM,
        access_expire_minutes=ACCESS_MINUTES,
        refresh_expire_days=REFRESH_DAYS,
    )


class TestCreateAccessToken:
    def test_produces_valid_jwt_decodable_with_same_secret(self, adapter: JWTTokenAdapter):
        token = adapter.create_access_token("alice")
        payload = jwt.decode(token, SECRET, algorithms=[ALGORITHM])
        assert payload["sub"] == "alice"
        assert payload["type"] == "access"
        assert "exp" in payload


class TestCreateRefreshToken:
    def test_refresh_token_has_longer_expiry_than_access(self, adapter: JWTTokenAdapter):
        access = adapter.create_access_token("bob")
        refresh = adapter.create_refresh_token("bob")

        access_payload = jwt.decode(access, SECRET, algorithms=[ALGORITHM])
        refresh_payload = jwt.decode(refresh, SECRET, algorithms=[ALGORITHM])

        assert refresh_payload["exp"] > access_payload["exp"]
        assert refresh_payload["type"] == "refresh"


class TestValidateToken:
    def test_valid_token_returns_username(self, adapter: JWTTokenAdapter):
        token = adapter.create_access_token("charlie")
        result = adapter.validate_token(token)
        assert result == "charlie"

    def test_expired_token_returns_none(self):
        """An expired token must return None (not raise)."""
        adapter = JWTTokenAdapter(
            secret_key=SECRET,
            algorithm=ALGORITHM,
            access_expire_minutes=0,
            refresh_expire_days=0,
        )
        # Manually create an already-expired token
        payload = {
            "sub": "dave",
            "exp": datetime.now(UTC) - timedelta(seconds=10),
            "type": "access",
        }
        expired_token = jwt.encode(payload, SECRET, algorithm=ALGORITHM)
        assert adapter.validate_token(expired_token) is None

    def test_wrong_signature_returns_none(self, adapter: JWTTokenAdapter):
        """A token signed with a different secret must return None."""
        payload = {
            "sub": "eve",
            "exp": datetime.now(UTC) + timedelta(hours=1),
            "type": "access",
        }
        bad_token = jwt.encode(payload, "wrong-secret", algorithm=ALGORITHM)
        assert adapter.validate_token(bad_token) is None

    def test_garbage_string_returns_none(self, adapter: JWTTokenAdapter):
        """A completely invalid string must return None."""
        assert adapter.validate_token("not.a.jwt.at.all") is None
