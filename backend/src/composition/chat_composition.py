from sqlalchemy.ext.asyncio import AsyncSession

from src.application.chat.services.chat_application_service import ChatApplicationService
from src.application.chat.use_cases.create_session import CreateSessionUseCase
from src.application.chat.use_cases.delete_session import DeleteSessionUseCase
from src.application.chat.use_cases.get_session_history import GetSessionHistoryUseCase
from src.application.chat.use_cases.list_sessions import ListSessionsUseCase
from src.application.chat.use_cases.send_message import SendMessageUseCase
from src.application.chat.use_cases.update_session_title import UpdateSessionTitleUseCase
from src.composition.rag_composition import build_rag_application_service
from src.infrastructure.chat.adapters.rag_adapter import InProcessRAGAdapter
from src.infrastructure.chat.repositories.chat_repository import ChatRepositoryImpl


def build_chat_application_service(db: AsyncSession) -> ChatApplicationService:
    """Wire all chat dependencies and return the application service."""
    chat_repo = ChatRepositoryImpl(db)

    rag_service = build_rag_application_service(db)
    rag_adapter = InProcessRAGAdapter(rag_service)

    return ChatApplicationService(
        create_session_use_case=CreateSessionUseCase(chat_repository=chat_repo),
        send_message_use_case=SendMessageUseCase(
            chat_repository=chat_repo, rag_port=rag_adapter
        ),
        get_session_history_use_case=GetSessionHistoryUseCase(chat_repository=chat_repo),
        list_sessions_use_case=ListSessionsUseCase(chat_repository=chat_repo),
        delete_session_use_case=DeleteSessionUseCase(chat_repository=chat_repo),
        update_session_title_use_case=UpdateSessionTitleUseCase(chat_repository=chat_repo),
    )
