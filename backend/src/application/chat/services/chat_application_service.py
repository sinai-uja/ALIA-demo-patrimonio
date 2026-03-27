from src.application.chat.dto.chat_dto import (
    CreateSessionDTO,
    MessageDTO,
    SendMessageDTO,
    SessionDTO,
    UpdateSessionDTO,
)
from src.application.chat.use_cases.create_session import CreateSessionUseCase
from src.application.chat.use_cases.delete_session import DeleteSessionUseCase
from src.application.chat.use_cases.get_session_history import GetSessionHistoryUseCase
from src.application.chat.use_cases.list_sessions import ListSessionsUseCase
from src.application.chat.use_cases.send_message import SendMessageUseCase
from src.application.chat.use_cases.update_session_title import UpdateSessionTitleUseCase


class ChatApplicationService:
    """Application service that exposes chat operations to the API layer."""

    def __init__(
        self,
        create_session_use_case: CreateSessionUseCase,
        send_message_use_case: SendMessageUseCase,
        get_session_history_use_case: GetSessionHistoryUseCase,
        list_sessions_use_case: ListSessionsUseCase,
        delete_session_use_case: DeleteSessionUseCase,
        update_session_title_use_case: UpdateSessionTitleUseCase,
    ) -> None:
        self._create_session = create_session_use_case
        self._send_message = send_message_use_case
        self._get_session_history = get_session_history_use_case
        self._list_sessions = list_sessions_use_case
        self._delete_session = delete_session_use_case
        self._update_session_title = update_session_title_use_case

    async def create_session(self, dto: CreateSessionDTO) -> SessionDTO:
        return await self._create_session.execute(dto)

    async def send_message(self, dto: SendMessageDTO) -> MessageDTO:
        return await self._send_message.execute(dto)

    async def get_history(self, session_id: str) -> list[MessageDTO]:
        return await self._get_session_history.execute(session_id)

    async def list_sessions(self, user_id: str | None = None) -> list[SessionDTO]:
        return await self._list_sessions.execute(user_id=user_id)

    async def delete_session(self, session_id: str, user_id: str | None = None) -> None:
        return await self._delete_session.execute(session_id, user_id=user_id)

    async def update_session_title(self, dto: UpdateSessionDTO) -> SessionDTO:
        return await self._update_session_title.execute(dto)
