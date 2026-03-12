import uuid

from src.application.chat.dto.chat_dto import SessionDTO, UpdateSessionDTO
from src.domain.chat.ports.chat_repository import ChatRepository


class UpdateSessionTitleUseCase:
    """Use case for updating a chat session title."""

    def __init__(self, chat_repository: ChatRepository) -> None:
        self._chat_repository = chat_repository

    async def execute(self, dto: UpdateSessionDTO) -> SessionDTO:
        session = await self._chat_repository.update_session_title(
            session_id=uuid.UUID(dto.session_id),
            title=dto.title,
        )
        return SessionDTO(
            id=str(session.id),
            title=session.title,
            created_at=str(session.created_at),
            updated_at=str(session.updated_at),
        )
