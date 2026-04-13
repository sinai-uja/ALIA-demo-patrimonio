"""Tests for auth use cases (login, validate_token, refresh_token, ensure_root_admin)."""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.auth.dto.auth_dto import LoginDTO, TokenPairDTO
from src.application.auth.exceptions import InvalidCredentialsError, InvalidTokenError
from src.application.auth.use_cases.ensure_root_admin import EnsureRootAdminUseCase
from src.application.auth.use_cases.login_use_case import LoginUseCase
from src.application.auth.use_cases.refresh_token_use_case import RefreshTokenUseCase
from src.application.auth.use_cases.validate_token_use_case import ValidateTokenUseCase
from src.domain.auth.entities.user import User, UserProfileType

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ADMIN_PT = UserProfileType(id=uuid.UUID("00000000-0000-0000-0000-0000000000a1"), name="admin")


def _make_user(username="testuser", profile_type=None):
    return User(
        id=uuid.uuid4(),
        username=username,
        password_hash="hashed",
        profile_type=profile_type or UserProfileType(
            id=uuid.uuid4(), name="user",
        ),
        created_at=datetime(2025, 1, 1),
    )


# ---------------------------------------------------------------------------
# LoginUseCase
# ---------------------------------------------------------------------------


@pytest.fixture
def login_uc():
    auth_port = AsyncMock()
    token_port = MagicMock()
    token_port.create_access_token.return_value = "access_tok"
    token_port.create_refresh_token.return_value = "refresh_tok"
    auth_port.authenticate.return_value = _make_user()
    return LoginUseCase(auth_port=auth_port, token_port=token_port), auth_port, token_port


@pytest.mark.asyncio
async def test_login_happy_path_returns_token_pair(login_uc):
    uc, _, _ = login_uc
    result = await uc.execute(LoginDTO(username="testuser", password="pass"))
    assert isinstance(result, TokenPairDTO)
    assert result.access_token == "access_tok"
    assert result.refresh_token == "refresh_tok"


@pytest.mark.asyncio
async def test_login_invalid_credentials_raises(login_uc):
    uc, auth_port, _ = login_uc
    auth_port.authenticate.return_value = None
    with pytest.raises(InvalidCredentialsError):
        await uc.execute(LoginDTO(username="bad", password="bad"))


# ---------------------------------------------------------------------------
# ValidateTokenUseCase
# ---------------------------------------------------------------------------


@pytest.fixture
def validate_uc():
    token_port = MagicMock()
    auth_port = AsyncMock()
    user = _make_user()
    token_port.validate_token.return_value = "testuser"
    auth_port.get_user_by_username.return_value = user
    return ValidateTokenUseCase(token_port=token_port, auth_port=auth_port), token_port, auth_port


@pytest.mark.asyncio
async def test_validate_token_happy_path_returns_user(validate_uc):
    uc, _, _ = validate_uc
    result = await uc.execute("valid_token")
    assert isinstance(result, User)
    assert result.username == "testuser"


@pytest.mark.asyncio
async def test_validate_token_invalid_token_raises(validate_uc):
    uc, token_port, _ = validate_uc
    token_port.validate_token.return_value = None
    with pytest.raises(InvalidTokenError):
        await uc.execute("invalid")


@pytest.mark.asyncio
async def test_validate_token_user_not_found_raises(validate_uc):
    uc, _, auth_port = validate_uc
    auth_port.get_user_by_username.return_value = None
    with pytest.raises(InvalidTokenError):
        await uc.execute("valid_token")


# ---------------------------------------------------------------------------
# RefreshTokenUseCase
# ---------------------------------------------------------------------------


@pytest.fixture
def refresh_uc():
    token_port = MagicMock()
    token_port.validate_token.return_value = "testuser"
    token_port.create_access_token.return_value = "new_access"
    token_port.create_refresh_token.return_value = "new_refresh"
    return RefreshTokenUseCase(token_port=token_port), token_port


@pytest.mark.asyncio
async def test_refresh_happy_path_returns_new_pair(refresh_uc):
    uc, _ = refresh_uc
    result = await uc.execute("old_refresh")
    assert isinstance(result, TokenPairDTO)
    assert result.access_token == "new_access"


@pytest.mark.asyncio
async def test_refresh_invalid_token_raises(refresh_uc):
    uc, token_port = refresh_uc
    token_port.validate_token.return_value = None
    with pytest.raises(InvalidTokenError):
        await uc.execute("expired_refresh")


# ---------------------------------------------------------------------------
# EnsureRootAdminUseCase
# ---------------------------------------------------------------------------


@pytest.fixture
def ensure_root_uc(mock_uow):
    auth_port = AsyncMock()
    auth_port.get_user_by_username.return_value = None
    auth_port.list_profile_types.return_value = []
    auth_port.create_profile_type.return_value = _ADMIN_PT
    auth_port.create_user.return_value = _make_user(username="root", profile_type=_ADMIN_PT)
    return EnsureRootAdminUseCase(auth_port=auth_port, unit_of_work=mock_uow), auth_port


@pytest.mark.asyncio
async def test_ensure_root_admin_creates_admin_when_not_exists(ensure_root_uc):
    uc, auth_port = ensure_root_uc
    await uc.execute("root", "password")
    auth_port.create_user.assert_awaited_once()
    auth_port.create_profile_type.assert_awaited_once()


@pytest.mark.asyncio
async def test_ensure_root_admin_noop_when_exists_with_admin_profile(ensure_root_uc):
    uc, auth_port = ensure_root_uc
    existing = _make_user(username="root", profile_type=_ADMIN_PT)
    auth_port.get_user_by_username.return_value = existing
    await uc.execute("root", "password")
    auth_port.create_user.assert_not_awaited()
    auth_port.create_profile_type.assert_not_awaited()


@pytest.mark.asyncio
async def test_ensure_root_admin_reattaches_admin_profile_if_wrong(ensure_root_uc, mock_uow):
    uc, auth_port = ensure_root_uc
    existing = _make_user(
        username="root",
        profile_type=UserProfileType(id=uuid.uuid4(), name="user"),
    )
    auth_port.get_user_by_username.return_value = existing
    await uc.execute("root", "password")
    auth_port.update_profile_type.assert_awaited_once()
    auth_port.create_user.assert_not_awaited()
