import uuid

from src.application.chat.dto.chat_dto import SessionDTO, UpdateSessionDTO
from src.domain.chat.ports.chat_repository import ChatRepository
from src.domain.shared.ports.unit_of_work import UnitOfWork


class UpdateSessionTitleUseCase:
    """Use case for updating a chat session title."""

    def __init__(
        self,
        chat_repository: ChatRepository,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._chat_repository = chat_repository
        self._uow = unit_of_work

    async def execute(self, dto: UpdateSessionDTO) -> SessionDTO:
        user_uuid = uuid.UUID(dto.user_id) if dto.user_id else None
        async with self._uow:
            session = await self._chat_repository.update_session_title(
                session_id=uuid.UUID(dto.session_id),
                title=dto.title,
                user_id=user_uuid,
            )
            result = SessionDTO(
                id=str(session.id),
                title=session.title,
                created_at=str(session.created_at),
                updated_at=str(session.updated_at),
            )
        return result
