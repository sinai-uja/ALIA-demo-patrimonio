"""Tests for SendMessageUseCase — chat context."""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.application.chat.dto.chat_dto import MessageDTO, SendMessageDTO
from src.application.chat.exceptions import SessionNotFoundError
from src.application.chat.use_cases.send_message import SendMessageUseCase
from src.application.shared.exceptions import LLMUnavailableError
from src.domain.chat.entities.message import Message
from src.domain.chat.entities.message_role import MessageRole
from src.domain.chat.services.intent_classifier import IntentClassifier, MessageIntent
from src.domain.chat.services.query_reformulator import QueryReformulator


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_SESSION_ID = str(uuid.uuid4())
_USER_ID = str(uuid.uuid4())


def _make_session(session_id=_SESSION_ID, user_id=_USER_ID):
    session = MagicMock()
    session.id = uuid.UUID(session_id)
    session.user_id = uuid.UUID(user_id)
    session.title = "Test session"
    return session


def _make_assistant_message(session_id=_SESSION_ID, content="assistant reply"):
    msg = MagicMock()
    msg.id = uuid.uuid4()
    msg.session_id = uuid.UUID(session_id)
    msg.role = MessageRole.ASSISTANT
    msg.content = content
    msg.sources = []
    msg.created_at = datetime(2025, 1, 1)
    return msg


@pytest.fixture
def mock_chat_repo():
    repo = AsyncMock()
    repo.get_session.return_value = _make_session()
    repo.get_messages.return_value = []
    repo.add_message.return_value = _make_assistant_message()
    return repo


@pytest.fixture
def mock_rag_port():
    port = AsyncMock()
    port.query.return_value = ("RAG answer", [])
    return port


@pytest.fixture
def mock_intent_classifier():
    classifier = AsyncMock(spec=IntentClassifier)
    classifier.classify.return_value = MessageIntent.RAG_QUERY
    return classifier


@pytest.fixture
def mock_query_reformulator():
    reformulator = MagicMock(spec=QueryReformulator)
    reformulator.reformulate.return_value = "reformulated query"
    return reformulator


@pytest.fixture
def mock_conversational_llm():
    port = AsyncMock()
    port.generate.return_value = "Conversational answer"
    return port


@pytest.fixture
def use_case(
    mock_chat_repo,
    mock_rag_port,
    mock_intent_classifier,
    mock_query_reformulator,
    mock_conversational_llm,
    mock_uow,
):
    return SendMessageUseCase(
        chat_repository=mock_chat_repo,
        rag_port=mock_rag_port,
        intent_classifier=mock_intent_classifier,
        query_reformulator=mock_query_reformulator,
        conversational_llm_port=mock_conversational_llm,
        unit_of_work=mock_uow,
    )


def _dto(**overrides):
    defaults = dict(
        session_id=_SESSION_ID,
        content="hello",
        user_id=_USER_ID,
    )
    defaults.update(overrides)
    return SendMessageDTO(**defaults)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_happy_path_returns_message_dto(use_case, mock_chat_repo):
    result = await use_case.execute(_dto())
    assert isinstance(result, MessageDTO)
    assert result.role == "assistant"
    mock_chat_repo.get_session.assert_awaited_once()


@pytest.mark.asyncio
async def test_session_not_found_raises(use_case, mock_chat_repo):
    mock_chat_repo.get_session.return_value = None
    with pytest.raises(SessionNotFoundError):
        await use_case.execute(_dto())


@pytest.mark.asyncio
async def test_session_not_owned_raises(use_case, mock_chat_repo):
    """get_session with mismatched user_id returns None -> SessionNotFoundError."""
    mock_chat_repo.get_session.return_value = None
    with pytest.raises(SessionNotFoundError):
        await use_case.execute(_dto(user_id=str(uuid.uuid4())))


@pytest.mark.asyncio
async def test_intent_conversational_calls_conversational_llm(
    use_case, mock_intent_classifier, mock_conversational_llm, mock_rag_port
):
    mock_intent_classifier.classify.return_value = MessageIntent.CONVERSATIONAL
    await use_case.execute(_dto())
    mock_conversational_llm.generate.assert_awaited_once()
    mock_rag_port.query.assert_not_awaited()


@pytest.mark.asyncio
async def test_intent_rag_query_calls_rag_port(
    use_case, mock_intent_classifier, mock_rag_port, mock_conversational_llm
):
    mock_intent_classifier.classify.return_value = MessageIntent.RAG_QUERY
    await use_case.execute(_dto())
    mock_rag_port.query.assert_awaited_once()
    mock_conversational_llm.generate.assert_not_awaited()


@pytest.mark.asyncio
async def test_intent_contextual_rag_reformulates_and_calls_rag(
    use_case, mock_intent_classifier, mock_query_reformulator, mock_rag_port
):
    mock_intent_classifier.classify.return_value = MessageIntent.CONTEXTUAL_RAG
    await use_case.execute(_dto())
    mock_query_reformulator.reformulate.assert_called_once()
    mock_rag_port.query.assert_awaited_once()


@pytest.mark.asyncio
async def test_rag_query_with_history_reformulates(
    use_case, mock_intent_classifier, mock_chat_repo, mock_query_reformulator, mock_rag_port
):
    """When intent is RAG_QUERY and there IS history, query is reformulated."""
    mock_intent_classifier.classify.return_value = MessageIntent.RAG_QUERY
    mock_chat_repo.get_messages.return_value = [
        Message(
            id=uuid.uuid4(),
            session_id=uuid.UUID(_SESSION_ID),
            role=MessageRole.USER,
            content="previous question",
        )
    ]
    await use_case.execute(_dto())
    mock_query_reformulator.reformulate.assert_called_once()
    mock_rag_port.query.assert_awaited_once()


@pytest.mark.asyncio
async def test_rag_query_without_history_uses_direct_query(
    use_case, mock_intent_classifier, mock_chat_repo, mock_query_reformulator, mock_rag_port
):
    """When intent is RAG_QUERY and there is NO history, query is NOT reformulated."""
    mock_intent_classifier.classify.return_value = MessageIntent.RAG_QUERY
    mock_chat_repo.get_messages.return_value = []
    await use_case.execute(_dto())
    mock_query_reformulator.reformulate.assert_not_called()


@pytest.mark.asyncio
async def test_llm_unavailable_in_classifier_falls_back_to_rag(
    use_case, mock_intent_classifier, mock_rag_port
):
    mock_intent_classifier.classify.side_effect = LLMUnavailableError("down")
    await use_case.execute(_dto())
    mock_rag_port.query.assert_awaited_once()


@pytest.mark.asyncio
async def test_user_message_saved_before_response(use_case, mock_chat_repo):
    await use_case.execute(_dto())
    # add_message is called twice: once for user, once for assistant
    assert mock_chat_repo.add_message.await_count == 2
    first_call = mock_chat_repo.add_message.call_args_list[0]
    assert first_call.kwargs["role"] == MessageRole.USER


@pytest.mark.asyncio
async def test_uow_entered_and_exited(use_case, mock_uow):
    await use_case.execute(_dto())
    mock_uow.__aenter__.assert_awaited_once()
    mock_uow.__aexit__.assert_awaited_once()


@pytest.mark.asyncio
async def test_rag_sources_propagated_to_assistant_message(
    use_case, mock_rag_port, mock_chat_repo
):
    mock_rag_port.query.return_value = (
        "answer with sources",
        [{"title": "Source 1", "url": "http://example.com", "score": 0.9}],
    )
    await use_case.execute(_dto())
    # The second add_message call (assistant) should include sources
    assistant_call = mock_chat_repo.add_message.call_args_list[1]
    assert len(assistant_call.kwargs["sources"]) == 1
