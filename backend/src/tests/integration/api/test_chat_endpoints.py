"""Integration tests for chat API endpoints."""

import uuid
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.v1.endpoints.auth.deps import get_current_user
from src.api.v1.endpoints.chat.deps import get_chat_service
from src.application.chat.dto.chat_dto import MessageDTO, SessionDTO
from src.application.chat.dto.source_dto import SourceDTO
from src.application.shared.exceptions import ResourceNotFoundError
from src.domain.auth.entities.user import User, UserProfileType
from src.main import app

_FAKE_USER = User(
    id=uuid.uuid4(),
    username="testuser",
    password_hash="hashed",
    profile_type=UserProfileType(id=uuid.uuid4(), name="investigador"),
)


def _session_dto(**overrides) -> SessionDTO:
    defaults = dict(
        id="session-1",
        title="Test session",
        created_at="2025-01-01T00:00:00",
        updated_at="2025-01-01T00:00:00",
    )
    defaults.update(overrides)
    return SessionDTO(**defaults)


def _message_dto(**overrides) -> MessageDTO:
    defaults = dict(
        id="msg-1",
        session_id="session-1",
        role="assistant",
        content="Hello there",
        sources=[],
        created_at="2025-01-01T00:00:00",
    )
    defaults.update(overrides)
    return MessageDTO(**defaults)


@pytest.fixture
def mock_chat_service():
    return AsyncMock()


@pytest.fixture
def client(mock_chat_service):
    app.dependency_overrides[get_chat_service] = lambda: mock_chat_service
    app.dependency_overrides[get_current_user] = lambda: _FAKE_USER
    yield AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    )
    app.dependency_overrides.clear()


class TestChatEndpoints:
    async def test_create_session_returns_201(self, client, mock_chat_service):
        mock_chat_service.create_session.return_value = _session_dto()
        resp = await client.post(
            "/api/v1/chat/sessions",
            json={"title": "My session"},
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["id"] == "session-1"
        assert body["title"] == "Test session"
        assert "created_at" in body
        assert "updated_at" in body

    async def test_list_sessions_returns_200(self, client, mock_chat_service):
        mock_chat_service.list_sessions.return_value = [
            _session_dto(id="s1"),
            _session_dto(id="s2"),
        ]
        resp = await client.get("/api/v1/chat/sessions")
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, list)
        assert len(body) == 2

    async def test_get_session_messages_returns_200(self, client, mock_chat_service):
        mock_chat_service.get_history.return_value = [
            _message_dto(id="m1"),
            _message_dto(id="m2", role="user", content="Hi"),
        ]
        resp = await client.get("/api/v1/chat/sessions/session-1/messages")
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, list)
        assert len(body) == 2
        assert body[0]["role"] == "assistant"

    async def test_get_session_messages_nonexistent_returns_404(
        self, client, mock_chat_service
    ):
        mock_chat_service.get_history.side_effect = ResourceNotFoundError(
            "Session not found"
        )
        resp = await client.get("/api/v1/chat/sessions/nonexistent/messages")
        assert resp.status_code == 404
        assert "Session not found" in resp.json()["detail"]

    async def test_send_message_returns_201(self, client, mock_chat_service):
        mock_chat_service.send_message.return_value = _message_dto(
            sources=[
                SourceDTO(
                    title="Source 1",
                    url="https://example.com",
                    score=0.9,
                    heritage_type="inmueble",
                    province="Jaen",
                )
            ],
        )
        resp = await client.post(
            "/api/v1/chat/sessions/session-1/messages",
            json={"content": "Tell me about heritage"},
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["role"] == "assistant"
        assert body["content"] == "Hello there"
        assert len(body["sources"]) == 1

    async def test_send_message_empty_content_returns_422(
        self, client, mock_chat_service
    ):
        resp = await client.post(
            "/api/v1/chat/sessions/session-1/messages",
            json={"content": ""},
        )
        assert resp.status_code == 422

    async def test_delete_session_returns_204(self, client, mock_chat_service):
        mock_chat_service.delete_session.return_value = None
        resp = await client.delete("/api/v1/chat/sessions/session-1")
        assert resp.status_code == 204

    async def test_update_session_returns_200(self, client, mock_chat_service):
        mock_chat_service.update_session_title.return_value = _session_dto(
            title="Updated title"
        )
        resp = await client.patch(
            "/api/v1/chat/sessions/session-1",
            json={"title": "Updated title"},
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated title"
