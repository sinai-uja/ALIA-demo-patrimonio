from uuid import UUID

from src.domain.chat.ports.chat_repository import ChatRepository


class DeleteSessionUseCase:
    """Deletes a chat session and all its messages."""

    def __init__(self, chat_repository: ChatRepository) -> None:
        self._chat_repository = chat_repository

    async def execute(self, session_id: str, user_id: str | None = None) -> None:
        user_uuid = UUID(user_id) if user_id else None
        await self._chat_repository.delete_session(UUID(session_id), user_id=user_uuid)
