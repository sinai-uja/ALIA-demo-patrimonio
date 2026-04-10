"""Integration tests for feedback API endpoints."""

import uuid
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.v1.endpoints.auth.deps import get_current_user
from src.api.v1.endpoints.feedback.deps import get_feedback_service
from src.application.feedback.dto.feedback_dto import FeedbackDTO
from src.domain.auth.entities.user import User, UserProfileType
from src.main import app

_FAKE_USER = User(
    id=uuid.uuid4(),
    username="testuser",
    password_hash="hashed",
    profile_type=UserProfileType(id=uuid.uuid4(), name="investigador"),
)


def _feedback_dto(**overrides) -> FeedbackDTO:
    defaults = dict(
        id="fb-1",
        user_id="testuser",
        target_type="search",
        target_id="target-1",
        value=1,
        created_at="2025-01-01T00:00:00",
        updated_at="2025-01-01T00:00:00",
    )
    defaults.update(overrides)
    return FeedbackDTO(**defaults)


@pytest.fixture
def mock_feedback_service():
    return AsyncMock()


@pytest.fixture
def client(mock_feedback_service):
    app.dependency_overrides[get_feedback_service] = lambda: mock_feedback_service
    app.dependency_overrides[get_current_user] = lambda: _FAKE_USER
    yield AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    )
    app.dependency_overrides.clear()


class TestFeedbackEndpoints:
    async def test_submit_feedback_returns_200(self, client, mock_feedback_service):
        mock_feedback_service.submit_feedback.return_value = _feedback_dto()
        resp = await client.put(
            "/api/v1/feedback",
            json={
                "target_type": "search",
                "target_id": "target-1",
                "value": 1,
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == "fb-1"
        assert body["target_type"] == "search"
        assert body["value"] == 1

    async def test_get_feedback_returns_200(self, client, mock_feedback_service):
        mock_feedback_service.get_feedback.return_value = _feedback_dto()
        resp = await client.get("/api/v1/feedback/search/target-1")
        assert resp.status_code == 200
        body = resp.json()
        assert body["target_id"] == "target-1"

    async def test_get_feedback_nonexistent_returns_404(
        self, client, mock_feedback_service
    ):
        mock_feedback_service.get_feedback.return_value = None
        resp = await client.get("/api/v1/feedback/search/nonexistent")
        assert resp.status_code == 404
        assert "Feedback not found" in resp.json()["detail"]

    async def test_delete_feedback_returns_204(self, client, mock_feedback_service):
        mock_feedback_service.delete_feedback.return_value = True
        resp = await client.delete("/api/v1/feedback/search/target-1")
        assert resp.status_code == 204

    async def test_delete_feedback_nonexistent_returns_404(
        self, client, mock_feedback_service
    ):
        mock_feedback_service.delete_feedback.return_value = False
        resp = await client.delete("/api/v1/feedback/search/nonexistent")
        assert resp.status_code == 404

    async def test_get_feedback_batch_returns_200(self, client, mock_feedback_service):
        mock_feedback_service.get_feedback_batch.return_value = {
            "target-1": 1,
            "target-2": -1,
        }
        resp = await client.get(
            "/api/v1/feedback/batch",
            params={
                "target_type": "search",
                "target_ids": ["target-1", "target-2"],
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["feedbacks"]["target-1"] == 1
        assert body["feedbacks"]["target-2"] == -1

    async def test_submit_search_result_feedback_returns_200(
        self, client, mock_feedback_service
    ):
        mock_feedback_service.submit_feedback.return_value = _feedback_dto(
            target_type="search_result",
            target_id="ficha-inmueble-12345",
        )
        resp = await client.put(
            "/api/v1/feedback",
            json={
                "target_type": "search_result",
                "target_id": "ficha-inmueble-12345",
                "value": 1,
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["target_type"] == "search_result"
        assert body["target_id"] == "ficha-inmueble-12345"

    async def test_submit_search_result_feedback_invalid_type_returns_422(
        self, client, mock_feedback_service
    ):
        resp = await client.put(
            "/api/v1/feedback",
            json={
                "target_type": "invalid_type",
                "target_id": "target-1",
                "value": 1,
            },
        )
        assert resp.status_code == 422
