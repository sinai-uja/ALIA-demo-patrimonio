"""Tests for chat session CRUD use cases (create, delete, update, list, get_history)."""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.chat.dto.chat_dto import (
    CreateSessionDTO,
    MessageDTO,
    SessionDTO,
    UpdateSessionDTO,
)
from src.application.chat.exceptions import SessionNotFoundError
from src.application.chat.use_cases.create_session import CreateSessionUseCase
from src.application.chat.use_cases.delete_session import DeleteSessionUseCase
from src.application.chat.use_cases.get_session_history import GetSessionHistoryUseCase
from src.application.chat.use_cases.list_sessions import ListSessionsUseCase
from src.application.chat.use_cases.update_session_title import UpdateSessionTitleUseCase
from src.domain.chat.entities.message import Message
from src.domain.chat.entities.message_role import MessageRole

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_USER_ID = str(uuid.uuid4())
_SESSION_ID = str(uuid.uuid4())
_NOW = datetime(2025, 6, 1, 12, 0, 0)


def _make_session_entity(sid=_SESSION_ID, title="Chat"):
    s = MagicMock()
    s.id = uuid.UUID(sid)
    s.title = title
    s.created_at = _NOW
    s.updated_at = _NOW
    s.message_count = 0
    return s


def _make_message_entity(sid=_SESSION_ID, role=MessageRole.USER, content="hi"):
    return Message(
        id=uuid.uuid4(),
        session_id=uuid.UUID(sid),
        role=role,
        content=content,
        sources=[],
        created_at=_NOW,
    )


# ---------------------------------------------------------------------------
# CreateSessionUseCase
# ---------------------------------------------------------------------------


@pytest.fixture
def create_uc(mock_uow):
    repo = AsyncMock()
    repo.create_session.return_value = _make_session_entity()
    return CreateSessionUseCase(chat_repository=repo, unit_of_work=mock_uow), repo


@pytest.mark.asyncio
async def test_create_session_returns_session_dto(create_uc):
    uc, _ = create_uc
    result = await uc.execute(CreateSessionDTO(title="My chat", user_id=_USER_ID))
    assert isinstance(result, SessionDTO)
    assert result.title == "Chat"


@pytest.mark.asyncio
async def test_create_session_calls_repo(create_uc):
    uc, repo = create_uc
    await uc.execute(CreateSessionDTO(user_id=_USER_ID))
    repo.create_session.assert_awaited_once()


# ---------------------------------------------------------------------------
# DeleteSessionUseCase
# ---------------------------------------------------------------------------


@pytest.fixture
def delete_uc(mock_uow):
    repo = AsyncMock()
    return DeleteSessionUseCase(chat_repository=repo, unit_of_work=mock_uow), repo


@pytest.mark.asyncio
async def test_delete_session_delegates_to_repo(delete_uc):
    uc, repo = delete_uc
    await uc.execute(_SESSION_ID, user_id=_USER_ID)
    repo.delete_session.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_session_propagates_repo_exception(delete_uc):
    uc, repo = delete_uc
    repo.delete_session.side_effect = SessionNotFoundError("nope")
    with pytest.raises(SessionNotFoundError):
        await uc.execute(str(uuid.uuid4()), user_id=_USER_ID)


# ---------------------------------------------------------------------------
# UpdateSessionTitleUseCase
# ---------------------------------------------------------------------------


@pytest.fixture
def update_uc(mock_uow):
    repo = AsyncMock()
    repo.update_session_title.return_value = _make_session_entity(title="Updated")
    return UpdateSessionTitleUseCase(chat_repository=repo, unit_of_work=mock_uow), repo


@pytest.mark.asyncio
async def test_update_title_returns_updated_dto(update_uc):
    uc, _ = update_uc
    dto = UpdateSessionDTO(session_id=_SESSION_ID, title="Updated", user_id=_USER_ID)
    result = await uc.execute(dto)
    assert isinstance(result, SessionDTO)
    assert result.title == "Updated"


# ---------------------------------------------------------------------------
# ListSessionsUseCase
# ---------------------------------------------------------------------------


@pytest.fixture
def list_uc():
    repo = AsyncMock()
    repo.list_sessions.return_value = [
        _make_session_entity(title="A"),
        _make_session_entity(sid=str(uuid.uuid4()), title="B"),
    ]
    return ListSessionsUseCase(chat_repository=repo), repo


@pytest.mark.asyncio
async def test_list_sessions_returns_list_of_dtos(list_uc):
    uc, _ = list_uc
    result = await uc.execute(user_id=_USER_ID)
    assert len(result) == 2
    assert all(isinstance(s, SessionDTO) for s in result)


@pytest.mark.asyncio
async def test_list_sessions_passes_user_id_to_repo(list_uc):
    uc, repo = list_uc
    await uc.execute(user_id=_USER_ID)
    call_kwargs = repo.list_sessions.call_args.kwargs
    assert call_kwargs["user_id"] == uuid.UUID(_USER_ID)


# ---------------------------------------------------------------------------
# GetSessionHistoryUseCase
# ---------------------------------------------------------------------------


@pytest.fixture
def history_uc():
    repo = AsyncMock()
    repo.get_session.return_value = _make_session_entity()
    repo.get_messages.return_value = [
        _make_message_entity(role=MessageRole.USER, content="hi"),
        _make_message_entity(role=MessageRole.ASSISTANT, content="hello"),
    ]
    return GetSessionHistoryUseCase(chat_repository=repo), repo


@pytest.mark.asyncio
async def test_get_history_returns_message_dtos(history_uc):
    uc, _ = history_uc
    result = await uc.execute(_SESSION_ID, user_id=_USER_ID)
    assert len(result) == 2
    assert all(isinstance(m, MessageDTO) for m in result)


@pytest.mark.asyncio
async def test_get_history_session_not_found_raises(history_uc):
    uc, repo = history_uc
    repo.get_session.return_value = None
    with pytest.raises(SessionNotFoundError):
        await uc.execute(str(uuid.uuid4()), user_id=_USER_ID)


@pytest.mark.asyncio
async def test_get_history_not_owned_raises(history_uc):
    """When get_session returns None (session not owned), raises SessionNotFoundError."""
    uc, repo = history_uc
    repo.get_session.return_value = None
    with pytest.raises(SessionNotFoundError):
        await uc.execute(_SESSION_ID, user_id=str(uuid.uuid4()))
