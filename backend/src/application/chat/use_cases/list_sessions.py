from uuid import UUID

from src.application.chat.dto.chat_dto import SessionDTO
from src.domain.chat.ports.chat_repository import ChatRepository


class ListSessionsUseCase:
    """Lists all chat sessions ordered by most recently updated."""

    def __init__(self, chat_repository: ChatRepository) -> None:
        self._chat_repository = chat_repository

    async def execute(self, user_id: str | None = None) -> list[SessionDTO]:
        user_uuid = UUID(user_id) if user_id else None
        sessions = await self._chat_repository.list_sessions(user_id=user_uuid)
        return [
            SessionDTO(
                id=str(s.id),
                title=s.title,
                created_at=s.created_at.isoformat(),
                updated_at=s.updated_at.isoformat(),
            )
            for s in sessions
        ]
