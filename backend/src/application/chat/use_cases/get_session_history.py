from uuid import UUID

from src.application.chat.dto.chat_dto import MessageDTO
from src.domain.chat.ports.chat_repository import ChatRepository


class GetSessionHistoryUseCase:
    """Retrieves all messages for a given chat session."""

    def __init__(self, chat_repository: ChatRepository) -> None:
        self._chat_repository = chat_repository

    async def execute(self, session_id: str) -> list[MessageDTO]:
        messages = await self._chat_repository.get_messages(UUID(session_id))
        return [
            MessageDTO(
                id=str(msg.id),
                session_id=str(msg.session_id),
                role=msg.role.value,
                content=msg.content,
                sources=msg.sources,
                created_at=msg.created_at.isoformat(),
            )
            for msg in messages
        ]
