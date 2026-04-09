from uuid import UUID

from src.application.chat.dto.chat_dto import CreateSessionDTO, SessionDTO
from src.domain.chat.ports.chat_repository import ChatRepository
from src.domain.shared.ports.unit_of_work import UnitOfWork


class CreateSessionUseCase:
    """Creates a new chat session."""

    def __init__(
        self,
        chat_repository: ChatRepository,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._chat_repository = chat_repository
        self._uow = unit_of_work

    async def execute(self, dto: CreateSessionDTO) -> SessionDTO:
        user_uuid = UUID(dto.user_id) if dto.user_id else None
        async with self._uow:
            session = await self._chat_repository.create_session(
                title=dto.title, user_id=user_uuid,
            )
            # Eagerly read attributes before the scope closes.
            result = SessionDTO(
                id=str(session.id),
                title=session.title,
                created_at=session.created_at.isoformat(),
                updated_at=session.updated_at.isoformat(),
                message_count=0,
            )
        return result
