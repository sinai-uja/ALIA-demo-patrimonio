from uuid import UUID

from src.application.chat.dto.chat_dto import MessageDTO, SendMessageDTO
from src.domain.chat.entities.message import Message
from src.domain.chat.entities.message_role import MessageRole
from src.domain.chat.ports.chat_repository import ChatRepository
from src.domain.chat.ports.rag_port import RAGPort

# Max recent messages to include for query contextualization
_HISTORY_WINDOW = 4


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

        # 2. Get recent history for query contextualization
        history = await self._chat_repository.get_messages(session_id)

        # 3. Save the user message
        await self._chat_repository.add_message(
            session_id=session_id,
            role=MessageRole.USER,
            content=dto.content,
            sources=[],
        )

        # 4. Build contextualized query from history + current message
        query = self._build_contextual_query(dto.content, history)

        # 5. Call RAG pipeline with contextualized query
        answer, sources = await self._rag_port.query(
            question=query,
            top_k=dto.top_k,
            heritage_type_filter=dto.heritage_type_filter,
            province_filter=dto.province_filter,
        )

        # 6. Save the assistant message with sources
        assistant_message = await self._chat_repository.add_message(
            session_id=session_id,
            role=MessageRole.ASSISTANT,
            content=answer,
            sources=sources,
        )

        # 7. Return the assistant MessageDTO
        return MessageDTO(
            id=str(assistant_message.id),
            session_id=str(assistant_message.session_id),
            role=assistant_message.role.value,
            content=assistant_message.content,
            sources=assistant_message.sources,
            created_at=assistant_message.created_at.isoformat(),
        )

    @staticmethod
    def _build_contextual_query(
        current: str, history: list[Message]
    ) -> str:
        """Enrich the current query with recent conversation context.

        If the user's message is short or uses pronouns/references that need
        context (e.g. "Y dónde está?"), prepend key content from the last
        assistant response to form a self-contained search query.
        """
        if not history:
            return current

        # Take the last few messages
        recent = history[-_HISTORY_WINDOW:]

        # Extract the last assistant message content (the answer)
        last_assistant = None
        for msg in reversed(recent):
            if msg.role == MessageRole.ASSISTANT:
                last_assistant = msg.content
                break

        if not last_assistant:
            return current

        # For short follow-up questions, prepend assistant context
        # This helps the embedding and FTS find relevant chunks
        # e.g. "Y dónde está?" → "La Alhambra es... Y dónde está?"
        summary = last_assistant[:200]
        return f"{summary} {current}"
