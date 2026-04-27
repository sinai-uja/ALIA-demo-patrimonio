"""Integration tests for admin trace endpoints with mocked dependencies."""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from src.application.shared.dto.trace_dto import (
    TraceListDTO,
    TraceSummaryDTO,
)
from src.domain.auth.entities.user import User, UserProfileType
from src.main import app

BASE = "http://test"
PREFIX = "/api/v1/admin/traces"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ADMIN_PROFILE = UserProfileType(id=uuid.uuid4(), name="admin")
REGULAR_PROFILE = UserProfileType(id=uuid.uuid4(), name="investigador")

ADMIN_USER = User(
    id=uuid.uuid4(),
    username="admin",
    password_hash="hashed",
    profile_type=ADMIN_PROFILE,
)

REGULAR_USER = User(
    id=uuid.uuid4(),
    username="regular",
    password_hash="hashed",
    profile_type=REGULAR_PROFILE,
)


def _override_deps(current_user: User, service: MagicMock):
    """Install FastAPI dependency overrides for auth + trace deps."""
    from src.api.v1.endpoints.admin import traces as traces_module
    from src.api.v1.endpoints.auth.deps import get_auth_service, get_current_user

    app.dependency_overrides[get_current_user] = lambda: current_user
    # The admin/traces router lives behind get_current_user dependency on the
    # router itself, so we also need a dummy auth service.
    app.dependency_overrides[get_auth_service] = lambda: AsyncMock()
    app.dependency_overrides[traces_module._get_trace_service] = lambda: service


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


def _mock_service() -> AsyncMock:
    return AsyncMock()


def _summary(
    *,
    pipeline_mode: str,
    execution_id: str,
    created_at: datetime,
    user_id: str | None = None,
    query: str = "test",
) -> TraceSummaryDTO:
    return TraceSummaryDTO(
        id=str(uuid.uuid4()),
        execution_type="route",
        execution_id=execution_id,
        user_id=user_id,
        username="admin",
        user_profile_type="admin",
        query=query,
        pipeline_mode=pipeline_mode,
        status="success",
        feedback_value=None,
        total_results=None,
        elapsed_ms=None,
        top_score=None,
        created_at=created_at.isoformat(),
    )


# ===========================================================================
# 1. Happy path: admin can fetch route history
# ===========================================================================


class TestListRouteHistory:
    async def test_returns_traces_with_aggregate_counts(self):
        route_id = str(uuid.uuid4())
        now = datetime.now(UTC)
        # Three traces sharing the same execution_id, in chronological order.
        traces = [
            _summary(
                pipeline_mode="route_generation_stream",
                execution_id=route_id,
                created_at=now,
                query="generate route",
            ),
            _summary(
                pipeline_mode="route_add_stop",
                execution_id=route_id,
                created_at=now + timedelta(minutes=1),
                query="+ Catedral (posición 2)",
            ),
            _summary(
                pipeline_mode="route_remove_stop",
                execution_id=route_id,
                created_at=now + timedelta(minutes=2),
                query="- Parada (posición 3)",
            ),
        ]
        svc = _mock_service()
        svc.list_route_history.return_value = TraceListDTO(
            traces=traces,
            total=len(traces),
            page=1,
            page_size=len(traces),
            total_pages=1,
        )
        _override_deps(ADMIN_USER, svc)

        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as c:
            resp = await c.get(
                f"{PREFIX}/by-route/{route_id}",
                headers={"Authorization": "Bearer fake-token"},
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["route_id"] == route_id
        assert len(body["traces"]) == 3
        assert body["aggregate"]["total_events"] == 3
        assert body["aggregate"]["generation_count"] == 1
        assert body["aggregate"]["additions_count"] == 1
        assert body["aggregate"]["removals_count"] == 1

    async def test_traces_are_ordered_chronologically(self):
        """The endpoint preserves the ordering returned by the service
        (which is ascending by created_at)."""
        route_id = str(uuid.uuid4())
        base = datetime.now(UTC)
        traces = [
            _summary(
                pipeline_mode="route_generation_stream",
                execution_id=route_id,
                created_at=base,
            ),
            _summary(
                pipeline_mode="route_add_stop",
                execution_id=route_id,
                created_at=base + timedelta(minutes=5),
            ),
            _summary(
                pipeline_mode="route_remove_stop",
                execution_id=route_id,
                created_at=base + timedelta(minutes=10),
            ),
        ]
        svc = _mock_service()
        svc.list_route_history.return_value = TraceListDTO(
            traces=traces,
            total=3,
            page=1,
            page_size=3,
            total_pages=1,
        )
        _override_deps(ADMIN_USER, svc)

        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as c:
            resp = await c.get(
                f"{PREFIX}/by-route/{route_id}",
                headers={"Authorization": "Bearer fake-token"},
            )

        assert resp.status_code == 200
        timestamps = [t["created_at"] for t in resp.json()["traces"]]
        assert timestamps == sorted(timestamps)

    async def test_excludes_other_admin_traces(self):
        """The service is called with the current admin's id as
        `exclude_admin_except`, so the list returned excludes other admins."""
        route_id = str(uuid.uuid4())
        # Service responds with only the calling admin's traces.
        only_my_trace = _summary(
            pipeline_mode="route_add_stop",
            execution_id=route_id,
            created_at=datetime.now(UTC),
            user_id=str(ADMIN_USER.id),
        )
        svc = _mock_service()
        svc.list_route_history.return_value = TraceListDTO(
            traces=[only_my_trace],
            total=1,
            page=1,
            page_size=1,
            total_pages=1,
        )
        _override_deps(ADMIN_USER, svc)

        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as c:
            resp = await c.get(
                f"{PREFIX}/by-route/{route_id}",
                headers={"Authorization": "Bearer fake-token"},
            )

        assert resp.status_code == 200
        # Confirm exclude_admin_except was threaded through.
        svc.list_route_history.assert_awaited_once_with(
            route_id, exclude_admin_except=str(ADMIN_USER.id),
        )
        body = resp.json()
        assert len(body["traces"]) == 1
        assert body["aggregate"]["total_events"] == 1


# ===========================================================================
# 2. Authorization: non-admin gets 403
# ===========================================================================


class TestRouteHistoryAuthorization:
    async def test_regular_user_gets_403(self):
        route_id = str(uuid.uuid4())
        svc = _mock_service()
        _override_deps(REGULAR_USER, svc)

        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as c:
            resp = await c.get(
                f"{PREFIX}/by-route/{route_id}",
                headers={"Authorization": "Bearer fake-token"},
            )

        assert resp.status_code == 403
        # Service was never invoked.
        svc.list_route_history.assert_not_called()
