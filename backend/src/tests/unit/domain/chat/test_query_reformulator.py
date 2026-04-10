"""Unit tests for QueryReformulator — pure domain, zero mocks."""

from datetime import datetime
from uuid import uuid4

import pytest

from src.domain.chat.entities.message import Message
from src.domain.chat.entities.message_role import MessageRole
from src.domain.chat.services.query_reformulator import QueryReformulator


def _make_message(role: MessageRole, content: str) -> Message:
    return Message(
        id=uuid4(),
        session_id=uuid4(),
        role=role,
        content=content,
    )


@pytest.fixture
def reformulator():
    return QueryReformulator()


class TestReformulate:
    def test_no_history_returns_original_query(self, reformulator):
        result = reformulator.reformulate("castillos en Jaén", [])

        assert result == "castillos en Jaén"

    def test_with_user_history_combines_queries(self, reformulator):
        history = [
            _make_message(MessageRole.USER, "castillos en Jaén"),
            _make_message(MessageRole.ASSISTANT, "Hay varios castillos..."),
        ]

        result = reformulator.reformulate("y en Málaga?", history)

        assert "castillos en Jaén" in result
        assert "y en Málaga?" in result
        assert " — " in result

    def test_only_assistant_history_returns_original(self, reformulator):
        history = [
            _make_message(MessageRole.ASSISTANT, "Bienvenido al sistema"),
        ]

        result = reformulator.reformulate("hola", history)

        assert result == "hola"

    def test_multiple_user_messages_uses_last(self, reformulator):
        history = [
            _make_message(MessageRole.USER, "primera pregunta"),
            _make_message(MessageRole.ASSISTANT, "respuesta 1"),
            _make_message(MessageRole.USER, "segunda pregunta"),
            _make_message(MessageRole.ASSISTANT, "respuesta 2"),
        ]

        result = reformulator.reformulate("más detalles", history)

        assert "segunda pregunta" in result
        assert "primera pregunta" not in result


class TestFindLastUserQuery:
    def test_finds_last_user_message_searching_backwards(self):
        history = [
            _make_message(MessageRole.USER, "first"),
            _make_message(MessageRole.ASSISTANT, "response"),
            _make_message(MessageRole.USER, "second"),
        ]

        result = QueryReformulator._find_last_user_query(history)

        assert result == "second"

    def test_returns_none_when_no_user_messages(self):
        history = [_make_message(MessageRole.ASSISTANT, "hello")]

        result = QueryReformulator._find_last_user_query(history)

        assert result is None

    def test_returns_none_for_empty_history(self):
        result = QueryReformulator._find_last_user_query([])

        assert result is None
