"""Integration tests for admin endpoints with mocked dependencies."""

import uuid
from unittest.mock import MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from src.application.auth.dto.auth_dto import UserInfoDTO
from src.domain.auth.entities.user import User, UserProfileType
from src.main import app

BASE = "http://test"
PREFIX = "/api/v1/admin"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ADMIN_PROFILE = UserProfileType(id=uuid.uuid4(), name="admin")
REGULAR_PROFILE = UserProfileType(id=uuid.uuid4(), name="investigador")

ROOT_ADMIN_USER = User(
    id=uuid.uuid4(),
    username="admin",  # matches settings.admin_username default
    password_hash="hashed",
    profile_type=ADMIN_PROFILE,
)

NON_ROOT_ADMIN_USER = User(
    id=uuid.uuid4(),
    username="other_admin",
    password_hash="hashed",
    profile_type=ADMIN_PROFILE,
)

REGULAR_USER = User(
    id=uuid.uuid4(),
    username="regular_user",
    password_hash="hashed",
    profile_type=REGULAR_PROFILE,
)

USER_NO_PROFILE = User(
    id=uuid.uuid4(),
    username="noprofile",
    password_hash="hashed",
    profile_type=None,
)


def _user_info(user: User) -> UserInfoDTO:
    return UserInfoDTO(
        id=str(user.id),
        username=user.username,
        profile_type=user.profile_type.name if user.profile_type else None,
        created_at="2025-01-01T00:00:00",
    )


ROOT_INFO = _user_info(ROOT_ADMIN_USER)
REGULAR_INFO = _user_info(REGULAR_USER)
NON_ROOT_ADMIN_INFO = _user_info(NON_ROOT_ADMIN_USER)


def _override_deps(current_user: User, service: MagicMock):
    """Install FastAPI dependency overrides for auth deps."""
    from src.api.v1.endpoints.auth.deps import get_auth_service, get_current_user

    app.dependency_overrides[get_current_user] = lambda: current_user
    app.dependency_overrides[get_auth_service] = lambda: service


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


def _mock_service() -> MagicMock:
    return MagicMock()


# ===========================================================================
# 1. Non-admin user gets 403 on all admin endpoints
# ===========================================================================


class TestNonAdminAccessDenied:
    """A user without admin profile_type must receive 403 on every endpoint."""

    async def test_list_users_returns_403_for_regular_user(self):
        svc = _mock_service()
        _override_deps(REGULAR_USER, svc)

        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as c:
            resp = await c.get(f"{PREFIX}/users")

        assert resp.status_code == 403
        assert "Admin access required" in resp.json()["detail"]

    async def test_create_user_returns_403_for_regular_user(self):
        svc = _mock_service()
        _override_deps(REGULAR_USER, svc)

        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as c:
            resp = await c.post(
                f"{PREFIX}/users",
                json={"username": "new", "password": "pw"},
            )

        assert resp.status_code == 403

    async def test_update_user_returns_403_for_regular_user(self):
        svc = _mock_service()
        _override_deps(REGULAR_USER, svc)

        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as c:
            resp = await c.put(
                f"{PREFIX}/users/{uuid.uuid4()}",
                json={"password": "new"},
            )

        assert resp.status_code == 403

    async def test_delete_user_returns_403_for_regular_user(self):
        svc = _mock_service()
        _override_deps(REGULAR_USER, svc)

        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as c:
            resp = await c.delete(f"{PREFIX}/users/{uuid.uuid4()}")

        assert resp.status_code == 403

    async def test_list_users_returns_403_for_user_without_profile(self):
        svc = _mock_service()
        _override_deps(USER_NO_PROFILE, svc)

        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as c:
            resp = await c.get(f"{PREFIX}/users")

        assert resp.status_code == 403


# ===========================================================================
# 2. Admin user can list users
# ===========================================================================


class TestListUsers:
    async def test_admin_can_list_users(self):
        svc = _mock_service()
        svc.list_users.return_value = [ROOT_INFO, REGULAR_INFO]
        _override_deps(ROOT_ADMIN_USER, svc)

        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as c:
            resp = await c.get(f"{PREFIX}/users")

        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 2
        usernames = {u["username"] for u in body}
        assert ROOT_ADMIN_USER.username in usernames
        assert REGULAR_USER.username in usernames

    async def test_list_users_returns_expected_fields(self):
        svc = _mock_service()
        svc.list_users.return_value = [REGULAR_INFO]
        _override_deps(ROOT_ADMIN_USER, svc)

        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as c:
            resp = await c.get(f"{PREFIX}/users")

        user = resp.json()[0]
        assert "id" in user
        assert "username" in user
        assert "profile_type" in user
        assert "created_at" in user

    async def test_non_root_admin_can_also_list_users(self):
        svc = _mock_service()
        svc.list_users.return_value = [REGULAR_INFO]
        _override_deps(NON_ROOT_ADMIN_USER, svc)

        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as c:
            resp = await c.get(f"{PREFIX}/users")

        assert resp.status_code == 200


# ===========================================================================
# 3. Root-admin protection: cannot modify or delete root admin user
# ===========================================================================


class TestRootAdminProtection:
    async def test_update_root_admin_returns_403(self):
        svc = _mock_service()
        svc.get_user_by_id.return_value = ROOT_INFO
        _override_deps(NON_ROOT_ADMIN_USER, svc)

        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as c:
            resp = await c.put(
                f"{PREFIX}/users/{ROOT_ADMIN_USER.id}",
                json={"password": "newpw"},
            )

        assert resp.status_code == 403
        assert "administrador raíz" in resp.json()["detail"]

    async def test_delete_root_admin_returns_403(self):
        svc = _mock_service()
        svc.get_user_by_id.return_value = ROOT_INFO
        _override_deps(NON_ROOT_ADMIN_USER, svc)

        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as c:
            resp = await c.delete(f"{PREFIX}/users/{ROOT_ADMIN_USER.id}")

        assert resp.status_code == 403
        assert "eliminar el administrador raíz" in resp.json()["detail"]

    async def test_even_root_admin_cannot_update_itself_via_root_protection(self):
        """Root admin user is also blocked from modifying its own record."""
        svc = _mock_service()
        svc.get_user_by_id.return_value = ROOT_INFO
        _override_deps(ROOT_ADMIN_USER, svc)

        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as c:
            resp = await c.put(
                f"{PREFIX}/users/{ROOT_ADMIN_USER.id}",
                json={"password": "newpw"},
            )

        assert resp.status_code == 403

    async def test_even_root_admin_cannot_delete_itself(self):
        svc = _mock_service()
        svc.get_user_by_id.return_value = ROOT_INFO
        _override_deps(ROOT_ADMIN_USER, svc)

        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as c:
            resp = await c.delete(f"{PREFIX}/users/{ROOT_ADMIN_USER.id}")

        assert resp.status_code == 403


# ===========================================================================
# 4. Non-root admin cannot create/assign admin profile type
# ===========================================================================


class TestAdminProfileTypeRestriction:
    async def test_non_root_admin_cannot_create_admin_user(self):
        svc = _mock_service()
        _override_deps(NON_ROOT_ADMIN_USER, svc)

        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as c:
            resp = await c.post(
                f"{PREFIX}/users",
                json={"username": "evil", "password": "pw", "profile_type": "admin"},
            )

        assert resp.status_code == 403
        assert "administrador raíz" in resp.json()["detail"]
        svc.create_user.assert_not_called()

    async def test_root_admin_can_create_admin_user(self):
        svc = _mock_service()
        new_info = UserInfoDTO(
            id=str(uuid.uuid4()),
            username="new_admin",
            profile_type="admin",
            created_at="2025-01-01T00:00:00",
        )
        svc.create_user.return_value = new_info
        _override_deps(ROOT_ADMIN_USER, svc)

        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as c:
            resp = await c.post(
                f"{PREFIX}/users",
                json={"username": "new_admin", "password": "pw", "profile_type": "admin"},
            )

        assert resp.status_code == 201
        assert resp.json()["username"] == "new_admin"
        assert resp.json()["profile_type"] == "admin"

    async def test_non_root_admin_cannot_assign_admin_profile_on_update(self):
        svc = _mock_service()
        svc.get_user_by_id.return_value = REGULAR_INFO
        _override_deps(NON_ROOT_ADMIN_USER, svc)

        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as c:
            resp = await c.put(
                f"{PREFIX}/users/{REGULAR_USER.id}",
                json={"profile_type": "admin"},
            )

        assert resp.status_code == 403
        assert "administrador raíz" in resp.json()["detail"]
        svc.update_user.assert_not_called()

    async def test_root_admin_can_assign_admin_profile_on_update(self):
        svc = _mock_service()
        svc.get_user_by_id.return_value = REGULAR_INFO
        updated = UserInfoDTO(
            id=str(REGULAR_USER.id),
            username=REGULAR_USER.username,
            profile_type="admin",
            created_at="2025-01-01T00:00:00",
        )
        svc.update_user.return_value = updated
        _override_deps(ROOT_ADMIN_USER, svc)

        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as c:
            resp = await c.put(
                f"{PREFIX}/users/{REGULAR_USER.id}",
                json={"profile_type": "admin"},
            )

        assert resp.status_code == 200
        assert resp.json()["profile_type"] == "admin"


# ===========================================================================
# 5. Happy-path CRUD operations
# ===========================================================================


class TestCRUDHappyPath:
    async def test_create_regular_user(self):
        svc = _mock_service()
        new_info = UserInfoDTO(
            id=str(uuid.uuid4()),
            username="researcher",
            profile_type="investigador",
            created_at="2025-01-01T00:00:00",
        )
        svc.create_user.return_value = new_info
        _override_deps(NON_ROOT_ADMIN_USER, svc)

        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as c:
            resp = await c.post(
                f"{PREFIX}/users",
                json={"username": "researcher", "password": "pw", "profile_type": "investigador"},
            )

        assert resp.status_code == 201
        assert resp.json()["username"] == "researcher"

    async def test_update_regular_user(self):
        svc = _mock_service()
        svc.get_user_by_id.return_value = REGULAR_INFO
        updated = UserInfoDTO(
            id=str(REGULAR_USER.id),
            username=REGULAR_USER.username,
            profile_type="investigador",
            created_at="2025-01-01T00:00:00",
        )
        svc.update_user.return_value = updated
        _override_deps(NON_ROOT_ADMIN_USER, svc)

        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as c:
            resp = await c.put(
                f"{PREFIX}/users/{REGULAR_USER.id}",
                json={"password": "newpw"},
            )

        assert resp.status_code == 200

    async def test_delete_regular_user(self):
        svc = _mock_service()
        svc.get_user_by_id.return_value = REGULAR_INFO
        _override_deps(ROOT_ADMIN_USER, svc)

        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as c:
            resp = await c.delete(f"{PREFIX}/users/{REGULAR_USER.id}")

        assert resp.status_code == 204
        svc.delete_user.assert_called_once()

    async def test_non_root_admin_cannot_delete_other_admin(self):
        svc = _mock_service()
        svc.get_user_by_id.return_value = NON_ROOT_ADMIN_INFO
        _override_deps(NON_ROOT_ADMIN_USER, svc)

        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as c:
            resp = await c.delete(f"{PREFIX}/users/{NON_ROOT_ADMIN_USER.id}")

        assert resp.status_code == 403
        assert "administrador raíz" in resp.json()["detail"]
        svc.delete_user.assert_not_called()


# ===========================================================================
# 6. Error handling
# ===========================================================================


class TestErrorHandling:
    async def test_update_nonexistent_user_returns_404(self):
        svc = _mock_service()
        svc.get_user_by_id.return_value = None
        _override_deps(ROOT_ADMIN_USER, svc)

        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as c:
            resp = await c.put(
                f"{PREFIX}/users/{uuid.uuid4()}",
                json={"password": "newpw"},
            )

        assert resp.status_code == 404
        assert resp.json()["detail"] == "User not found"

    async def test_delete_nonexistent_user_returns_404(self):
        svc = _mock_service()
        svc.get_user_by_id.return_value = None
        _override_deps(ROOT_ADMIN_USER, svc)

        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as c:
            resp = await c.delete(f"{PREFIX}/users/{uuid.uuid4()}")

        assert resp.status_code == 404

    async def test_create_user_with_duplicate_username_returns_400(self):
        svc = _mock_service()
        svc.create_user.side_effect = ValueError("Username already exists")
        _override_deps(ROOT_ADMIN_USER, svc)

        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as c:
            resp = await c.post(
                f"{PREFIX}/users",
                json={"username": "existing", "password": "pw"},
            )

        assert resp.status_code == 400
        assert "Username already exists" in resp.json()["detail"]

    async def test_update_user_value_error_returns_400(self):
        svc = _mock_service()
        svc.get_user_by_id.return_value = REGULAR_INFO
        svc.update_user.side_effect = ValueError("Invalid profile type")
        _override_deps(ROOT_ADMIN_USER, svc)

        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as c:
            resp = await c.put(
                f"{PREFIX}/users/{REGULAR_USER.id}",
                json={"profile_type": "nonexistent"},
            )

        assert resp.status_code == 400
        assert "Invalid profile type" in resp.json()["detail"]
