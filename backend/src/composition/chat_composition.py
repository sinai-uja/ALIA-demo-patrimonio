from sqlalchemy.ext.asyncio import AsyncSession

from src.application.chat.services.chat_application_service import ChatApplicationService
from src.application.chat.use_cases.create_session import CreateSessionUseCase
from src.application.chat.use_cases.delete_session import DeleteSessionUseCase
from src.application.chat.use_cases.get_session_history import GetSessionHistoryUseCase
from src.application.chat.use_cases.list_sessions import ListSessionsUseCase
from src.application.chat.use_cases.send_message import SendMessageUseCase
from src.application.chat.use_cases.update_session_title import UpdateSessionTitleUseCase
from src.composition.rag_composition import build_rag_application_service
from src.config import settings
from src.domain.chat.services.intent_classifier import IntentClassifier
from src.domain.chat.services.query_reformulator import QueryReformulator
from src.infrastructure.chat.adapters.conversational_llm_adapter import ConversationalLLMAdapter
from src.infrastructure.chat.adapters.gemini_conversational_adapter import (
    GeminiConversationalAdapter,
)
from src.infrastructure.chat.adapters.rag_adapter import InProcessRAGAdapter
from src.infrastructure.chat.repositories.chat_repository import ChatRepositoryImpl


def build_chat_application_service(db: AsyncSession) -> ChatApplicationService:
    """Wire all chat dependencies and return the application service."""
    chat_repo = ChatRepositoryImpl(db)

    rag_service = build_rag_application_service(db)
    rag_adapter = InProcessRAGAdapter(rag_service)

    conversational_llm = (
        GeminiConversationalAdapter()
        if settings.llm_provider == "gemini"
        else ConversationalLLMAdapter()
    )
    intent_classifier = IntentClassifier(llm_port=conversational_llm)
    query_reformulator = QueryReformulator()

    return ChatApplicationService(
        create_session_use_case=CreateSessionUseCase(chat_repository=chat_repo),
        send_message_use_case=SendMessageUseCase(
            chat_repository=chat_repo,
            rag_port=rag_adapter,
            intent_classifier=intent_classifier,
            query_reformulator=query_reformulator,
            conversational_llm_port=conversational_llm,
        ),
        get_session_history_use_case=GetSessionHistoryUseCase(chat_repository=chat_repo),
        list_sessions_use_case=ListSessionsUseCase(chat_repository=chat_repo),
        delete_session_use_case=DeleteSessionUseCase(chat_repository=chat_repo),
        update_session_title_use_case=UpdateSessionTitleUseCase(chat_repository=chat_repo),
    )
