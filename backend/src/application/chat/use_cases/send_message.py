import logging
from uuid import UUID

from src.application.chat.dto.chat_dto import MessageDTO, SendMessageDTO
from src.application.chat.dto.source_dto import SourceDTO
from src.application.chat.exceptions import SessionNotFoundError
from src.domain.chat.entities.message_role import MessageRole
from src.domain.chat.ports.chat_repository import ChatRepository
from src.domain.chat.ports.llm_port import ConversationalLLMPort
from src.domain.chat.ports.rag_port import RAGPort
from src.domain.chat.prompts import CONVERSATIONAL_SYSTEM_PROMPT
from src.domain.chat.services.intent_classifier import IntentClassifier, MessageIntent
from src.domain.chat.services.query_reformulator import QueryReformulator
from src.domain.shared.ports.unit_of_work import UnitOfWork
from src.application.shared.exceptions import LLMUnavailableError

logger = logging.getLogger("iaph.chat.send_message")


class SendMessageUseCase:
    """Sends a user message, classifies intent, routes to RAG or conversational LLM."""

    def __init__(
        self,
        chat_repository: ChatRepository,
        rag_port: RAGPort,
        intent_classifier: IntentClassifier,
        query_reformulator: QueryReformulator,
        conversational_llm_port: ConversationalLLMPort,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._chat_repository = chat_repository
        self._rag_port = rag_port
        self._intent_classifier = intent_classifier
        self._query_reformulator = query_reformulator
        self._conversational_llm_port = conversational_llm_port
        self._uow = unit_of_work

    async def execute(self, dto: SendMessageDTO) -> MessageDTO:
        session_id = UUID(dto.session_id)
        user_uuid = UUID(dto.user_id) if dto.user_id else None
        logger.info("Processing message for session %s: %s", dto.session_id, dto.content[:80])

        async with self._uow:
            # 1. Verify session exists and is owned by the actor
            session = await self._chat_repository.get_session(session_id, user_id=user_uuid)
            if session is None:
                raise SessionNotFoundError(f"Session {dto.session_id} not found")

            # 2. Get recent history for intent classification and context
            history = await self._chat_repository.get_messages(session_id)

            # 3. Save the user message
            await self._chat_repository.add_message(
                session_id=session_id,
                role=MessageRole.USER,
                content=dto.content,
                sources=[],
            )

            # 4. Classify intent via LLM. If the LLM adapter is unavailable we
            # fall back to a plain RAG query so the user still gets an answer.
            try:
                intent = await self._intent_classifier.classify(dto.content, history)
            except LLMUnavailableError:
                logger.warning(
                    "Intent classification unavailable, defaulting to RAG_QUERY",
                    exc_info=True,
                )
                intent = MessageIntent.RAG_QUERY

            # 5. Route based on intent
            if intent == MessageIntent.CONVERSATIONAL:
                logger.info("Routing to conversational LLM (no RAG)")
                answer = await self._conversational_llm_port.generate(
                    CONVERSATIONAL_SYSTEM_PROMPT, dto.content
                )
                sources = []

            elif intent == MessageIntent.CONTEXTUAL_RAG:
                reformulated = self._query_reformulator.reformulate(dto.content, history)
                logger.info("Routing to RAG with reformulated query: %s", reformulated[:120])
                answer, sources = await self._rag_port.query(
                    question=reformulated,
                    top_k=dto.top_k,
                    heritage_type_filter=dto.heritage_type_filter,
                    province_filter=dto.province_filter,
                )

            else:  # RAG_QUERY
                # If there's conversation history, enrich the query with context
                # to avoid losing intent on follow-up questions misclassified as new queries
                if history:
                    reformulated = self._query_reformulator.reformulate(
                        dto.content, history,
                    )
                    logger.info(
                        "Routing to RAG with context-enriched query: %s",
                        reformulated[:120],
                    )
                    query = reformulated
                else:
                    logger.info("Routing to RAG with direct query")
                    query = dto.content
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

            logger.info(
                "Response: %d chars, %d sources, intent=%s",
                len(answer), len(sources), intent.value,
            )

            # 7. Build the assistant MessageDTO before the UoW closes
            result = MessageDTO(
                id=str(assistant_message.id),
                session_id=str(assistant_message.session_id),
                role=assistant_message.role.value,
                content=assistant_message.content,
                sources=[_source_dict_to_dto(s) for s in assistant_message.sources],
                created_at=assistant_message.created_at.isoformat(),
            )
        return result


def _source_dict_to_dto(source: dict) -> SourceDTO:
    """Map a raw source dict (as produced by the RAG port) to a typed DTO."""
    return SourceDTO(
        title=source.get("title", ""),
        url=source.get("url", ""),
        score=float(source.get("score", 0.0)),
        heritage_type=source.get("heritage_type", ""),
        province=source.get("province", ""),
        municipality=source.get("municipality"),
        metadata=source.get("metadata"),
    )
