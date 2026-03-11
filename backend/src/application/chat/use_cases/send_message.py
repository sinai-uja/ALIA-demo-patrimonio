from uuid import UUID

from src.application.chat.dto.chat_dto import MessageDTO, SendMessageDTO
from src.domain.chat.entities.message_role import MessageRole
from src.domain.chat.ports.chat_repository import ChatRepository
from src.domain.chat.ports.rag_port import RAGPort


class SendMessageUseCase:
    """Sends a user message, invokes the RAG pipeline, and stores the assistant reply."""

    def __init__(self, chat_repository: ChatRepository, rag_port: RAGPort) -> None:
        self._chat_repository = chat_repository
        self._rag_port = rag_port

    async def execute(self, dto: SendMessageDTO) -> MessageDTO:
        session_id = UUID(dto.session_id)

        # 1. Verify session exists
        session = await self._chat_repository.get_session(session_id)
        if session is None:
            raise ValueError(f"Session {dto.session_id} not found")

        # 2. Save the user message
        await self._chat_repository.add_message(
            session_id=session_id,
            role=MessageRole.USER,
            content=dto.content,
            sources=[],
        )

        # 3. Call RAG pipeline
        answer, sources = await self._rag_port.query(
            question=dto.content,
            top_k=dto.top_k,
            heritage_type_filter=dto.heritage_type_filter,
            province_filter=dto.province_filter,
        )

        # 4. Save the assistant message with sources
        assistant_message = await self._chat_repository.add_message(
            session_id=session_id,
            role=MessageRole.ASSISTANT,
            content=answer,
            sources=sources,
        )

        # 5. Return the assistant MessageDTO
        return MessageDTO(
            id=str(assistant_message.id),
            session_id=str(assistant_message.session_id),
            role=assistant_message.role.value,
            content=assistant_message.content,
            sources=assistant_message.sources,
            created_at=assistant_message.created_at.isoformat(),
        )
