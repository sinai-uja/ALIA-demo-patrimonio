from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.chat.entities.chat_session import ChatSession
from src.domain.chat.entities.message import Message
from src.domain.chat.entities.message_role import MessageRole


class ChatRepository(ABC):
    """Port for chat persistence operations."""

    @abstractmethod
    async def create_session(self, title: str) -> ChatSession: ...

    @abstractmethod
    async def get_session(self, session_id: UUID) -> ChatSession | None: ...

    @abstractmethod
    async def list_sessions(self) -> list[ChatSession]: ...

    @abstractmethod
    async def delete_session(self, session_id: UUID) -> None: ...

    @abstractmethod
    async def add_message(
        self,
        session_id: UUID,
        role: MessageRole,
        content: str,
        sources: list[dict],
    ) -> Message: ...

    @abstractmethod
    async def get_messages(self, session_id: UUID) -> list[Message]: ...
