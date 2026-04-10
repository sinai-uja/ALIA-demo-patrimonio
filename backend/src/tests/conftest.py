"""Shared test fixtures for the IAPH RAG backend test suite."""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from src.domain.auth.entities.user import User, UserProfileType


@pytest.fixture
def mock_uow():
    """Async UnitOfWork mock that acts as a no-op context manager."""
    uow = AsyncMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=False)
    return uow


@pytest.fixture
def sample_user() -> User:
    """A regular (non-admin) user for tests that need a domain User entity."""
    return User(
        id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        username="testuser",
        password_hash="hashed_password",
        profile_type=UserProfileType(
            id=uuid.UUID("00000000-0000-0000-0000-0000000000a1"),
            name="user",
        ),
        created_at=datetime(2025, 1, 1, 0, 0, 0),
    )


@pytest.fixture
def sample_admin() -> User:
    """An admin user for tests that need elevated privileges."""
    return User(
        id=uuid.UUID("00000000-0000-0000-0000-000000000002"),
        username="admin",
        password_hash="hashed_password",
        profile_type=UserProfileType(
            id=uuid.UUID("00000000-0000-0000-0000-0000000000a2"),
            name="admin",
        ),
        created_at=datetime(2025, 1, 1, 0, 0, 0),
    )
