"""Tests for AuthApplicationService — admin business rules."""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from src.application.auth.dto.auth_dto import (
    CreateUserDTO,
    UpdateProfileTypeDTO,
    UpdateUserDTO,
)
from src.application.auth.dto.user_dto import UserDTO
from src.application.auth.exceptions import (
    AdminOnlyActionError,
    ProfileTypeNotFoundError,
    ProfileTypeProtectedError,
    RootAdminProtectedError,
    UserNotFoundError,
)
from src.application.auth.services.auth_application_service import AuthApplicationService
from src.domain.auth.entities.user import User, UserProfileType

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ROOT_USERNAME = "root_admin"
_ADMIN_PT = UserProfileType(id=uuid.uuid4(), name="admin")
_USER_PT = UserProfileType(id=uuid.uuid4(), name="user")


def _make_user(username="regular", profile_type=None):
    return User(
        id=uuid.uuid4(),
        username=username,
        password_hash="hashed",
        profile_type=profile_type or _USER_PT,
        created_at=datetime(2025, 1, 1),
    )


def _root_admin():
    return _make_user(username=_ROOT_USERNAME, profile_type=_ADMIN_PT)


def _non_root_admin():
    return _make_user(username="other_admin", profile_type=_ADMIN_PT)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def auth_port():
    port = AsyncMock()
    port.list_users.return_value = []
    port.get_user_by_id.return_value = None
    port.create_user.return_value = _make_user()
    port.update_user.return_value = _make_user()
    port.delete_user.return_value = None
    port.list_profile_types_with_counts.return_value = []
    port.create_profile_type.return_value = _USER_PT
    port.rename_profile_type.return_value = _USER_PT
    port.delete_profile_type.return_value = None
    return port


@pytest.fixture
def service(auth_port, mock_uow):
    return AuthApplicationService(
        login_use_case=AsyncMock(),
        validate_token_use_case=AsyncMock(),
        refresh_token_use_case=AsyncMock(),
        ensure_root_admin_use_case=AsyncMock(),
        auth_port=auth_port,
        unit_of_work=mock_uow,
        root_admin_username=_ROOT_USERNAME,
    )


# ---------------------------------------------------------------------------
# create_user
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_user_regular_by_root_admin(service, auth_port):
    result = await service.create_user(
        CreateUserDTO(username="new_user", password="pass", profile_type_name="user"),
        actor=_root_admin(),
    )
    assert isinstance(result, UserDTO)
    auth_port.create_user.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_user_regular_by_non_root_admin(service, auth_port):
    result = await service.create_user(
        CreateUserDTO(username="new_user", password="pass", profile_type_name="user"),
        actor=_non_root_admin(),
    )
    assert isinstance(result, UserDTO)


@pytest.mark.asyncio
async def test_create_admin_user_by_root_admin(service, auth_port):
    result = await service.create_user(
        CreateUserDTO(username="new_admin", password="pass", profile_type_name="admin"),
        actor=_root_admin(),
    )
    assert isinstance(result, UserDTO)


@pytest.mark.asyncio
async def test_create_admin_user_by_non_root_raises(service):
    with pytest.raises(AdminOnlyActionError):
        await service.create_user(
            CreateUserDTO(username="new_admin", password="pass", profile_type_name="admin"),
            actor=_non_root_admin(),
        )


# ---------------------------------------------------------------------------
# delete_user
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_user_not_found_raises(service, auth_port):
    auth_port.get_user_by_id.return_value = None
    with pytest.raises(UserNotFoundError):
        await service.delete_user(uuid.uuid4(), actor=_root_admin())


@pytest.mark.asyncio
async def test_delete_root_admin_raises(service, auth_port):
    auth_port.get_user_by_id.return_value = _root_admin()
    with pytest.raises(RootAdminProtectedError):
        await service.delete_user(uuid.uuid4(), actor=_root_admin())


@pytest.mark.asyncio
async def test_delete_other_admin_by_non_root_raises(service, auth_port):
    target = _non_root_admin()
    auth_port.get_user_by_id.return_value = target
    with pytest.raises(AdminOnlyActionError):
        await service.delete_user(target.id, actor=_non_root_admin())


@pytest.mark.asyncio
async def test_delete_regular_user_by_admin(service, auth_port, mock_uow):
    target = _make_user(username="victim")
    auth_port.get_user_by_id.return_value = target
    await service.delete_user(target.id, actor=_root_admin())
    auth_port.delete_user.assert_awaited_once()
    mock_uow.__aenter__.assert_awaited()


# ---------------------------------------------------------------------------
# update_user
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_root_admin_raises(service, auth_port):
    auth_port.get_user_by_id.return_value = _root_admin()
    with pytest.raises(RootAdminProtectedError):
        await service.update_user(
            UpdateUserDTO(user_id=uuid.uuid4(), password="new"),
            actor=_root_admin(),
        )


@pytest.mark.asyncio
async def test_update_user_not_found_raises(service, auth_port):
    auth_port.get_user_by_id.return_value = None
    with pytest.raises(UserNotFoundError):
        await service.update_user(
            UpdateUserDTO(user_id=uuid.uuid4(), password="new"),
            actor=_root_admin(),
        )


@pytest.mark.asyncio
async def test_update_user_assign_admin_by_non_root_raises(service, auth_port):
    target = _make_user(username="victim")
    auth_port.get_user_by_id.return_value = target
    with pytest.raises(AdminOnlyActionError):
        await service.update_user(
            UpdateUserDTO(user_id=target.id, profile_type_name="admin"),
            actor=_non_root_admin(),
        )


# ---------------------------------------------------------------------------
# rename_profile_type
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rename_admin_profile_type_raises(service, auth_port):
    auth_port.list_profile_types_with_counts.return_value = [(_ADMIN_PT, 1)]
    with pytest.raises(ProfileTypeProtectedError):
        await service.rename_profile_type(
            UpdateProfileTypeDTO(profile_type_id=_ADMIN_PT.id, name="superadmin"),
        )


@pytest.mark.asyncio
async def test_rename_nonexistent_profile_type_raises(service, auth_port):
    auth_port.list_profile_types_with_counts.return_value = []
    with pytest.raises(ProfileTypeNotFoundError):
        await service.rename_profile_type(
            UpdateProfileTypeDTO(profile_type_id=uuid.uuid4(), name="newname"),
        )


# ---------------------------------------------------------------------------
# delete_profile_type
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_admin_profile_type_raises(service, auth_port):
    auth_port.list_profile_types_with_counts.return_value = [(_ADMIN_PT, 1)]
    with pytest.raises(ProfileTypeProtectedError):
        await service.delete_profile_type(_ADMIN_PT.id)


@pytest.mark.asyncio
async def test_delete_nonexistent_profile_type_raises(service, auth_port):
    auth_port.list_profile_types_with_counts.return_value = []
    with pytest.raises(ProfileTypeNotFoundError):
        await service.delete_profile_type(uuid.uuid4())


# ---------------------------------------------------------------------------
# UoW wraps writes
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_user_wraps_in_uow(service, auth_port, mock_uow):
    await service.create_user(
        CreateUserDTO(username="u", password="p"),
        actor=_root_admin(),
    )
    mock_uow.__aenter__.assert_awaited()
    mock_uow.__aexit__.assert_awaited()
