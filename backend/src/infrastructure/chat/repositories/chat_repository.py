import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.chat.entities.chat_session import ChatSession
from src.domain.chat.entities.message import Message
from src.domain.chat.entities.message_role import MessageRole
from src.domain.chat.ports.chat_repository import ChatRepository
from src.infrastructure.chat.models import ChatMessageModel, ChatSessionModel

logger = logging.getLogger("iaph.chat.repository")


class ChatRepositoryImpl(ChatRepository):
    """Async SQLAlchemy implementation of the ChatRepository port."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create_session(
        self, title: str, user_id: uuid.UUID | None = None,
    ) -> ChatSession:
        model = ChatSessionModel(id=uuid.uuid4(), title=title, user_id=user_id)
        self._db.add(model)
        try:
            await self._db.flush()
            await self._db.refresh(model)
        except Exception:
            logger.error(
                "Failed to create chat session title=%r user_id=%s",
                title, user_id, exc_info=True,
            )
            raise
        return self._to_session_entity(model)

    async def get_session(
        self, session_id: uuid.UUID, user_id: uuid.UUID | None = None,
    ) -> ChatSession | None:
        stmt = select(ChatSessionModel).where(ChatSessionModel.id == session_id)
        if user_id is not None:
            stmt = stmt.where(ChatSessionModel.user_id == user_id)
        try:
            result = await self._db.execute(stmt)
        except Exception:
            logger.error(
                "Failed to get chat session session_id=%s user_id=%s",
                session_id, user_id, exc_info=True,
            )
            raise
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._to_session_entity(model)

    async def list_sessions(self, user_id: uuid.UUID | None = None) -> list[ChatSession]:
        stmt = select(ChatSessionModel).order_by(ChatSessionModel.updated_at.desc())
        if user_id is not None:
            stmt = stmt.where(ChatSessionModel.user_id == user_id)
        try:
            result = await self._db.execute(stmt)
        except Exception:
            logger.error("Failed to list chat sessions user_id=%s", user_id, exc_info=True)
            raise
        return [self._to_session_entity(m) for m in result.scalars().all()]

    async def delete_session(
        self, session_id: uuid.UUID, user_id: uuid.UUID | None = None,
    ) -> None:
        stmt = delete(ChatSessionModel).where(ChatSessionModel.id == session_id)
        if user_id is not None:
            stmt = stmt.where(ChatSessionModel.user_id == user_id)
        try:
            await self._db.execute(stmt)
        except Exception:
            logger.error(
                "Failed to delete chat session session_id=%s user_id=%s",
                session_id, user_id, exc_info=True,
            )
            raise

    async def update_session_title(
        self, session_id: uuid.UUID, title: str, user_id: uuid.UUID | None = None,
    ) -> ChatSession:
        stmt = (
            update(ChatSessionModel)
            .where(ChatSessionModel.id == session_id)
            .values(title=title)
        )
        if user_id is not None:
            stmt = stmt.where(ChatSessionModel.user_id == user_id)
        try:
            await self._db.execute(stmt)
            await self._db.flush()
        except Exception:
            logger.error(
                "Failed to update chat session title session_id=%s",
                session_id, exc_info=True,
            )
            raise

        get_stmt = select(ChatSessionModel).where(ChatSessionModel.id == session_id)
        if user_id is not None:
            get_stmt = get_stmt.where(ChatSessionModel.user_id == user_id)
        try:
            result = await self._db.execute(get_stmt)
        except Exception:
            logger.error(
                "Failed to re-fetch chat session after title update session_id=%s",
                session_id, exc_info=True,
            )
            raise
        model = result.scalar_one_or_none()
        if model is None:
            raise ValueError(f"Session {session_id} not found")
        return self._to_session_entity(model)

    async def add_message(
        self,
        session_id: uuid.UUID,
        role: MessageRole,
        content: str,
        sources: list[dict],
    ) -> Message:
        model = ChatMessageModel(
            id=uuid.uuid4(),
            session_id=session_id,
            role=role.value,
            content=content,
            sources=sources,
        )
        self._db.add(model)

        try:
            # Update session updated_at
            await self._db.execute(
                update(ChatSessionModel)
                .where(ChatSessionModel.id == session_id)
                .values(updated_at=datetime.now(UTC))
            )

            await self._db.flush()
            await self._db.refresh(model)
        except Exception:
            logger.error(
                "Failed to add message to chat session session_id=%s role=%s",
                session_id, role.value, exc_info=True,
            )
            raise
        return self._to_message_entity(model)

    async def get_messages(self, session_id: uuid.UUID) -> list[Message]:
        try:
            result = await self._db.execute(
                select(ChatMessageModel)
                .where(ChatMessageModel.session_id == session_id)
                .order_by(ChatMessageModel.created_at.asc())
            )
        except Exception:
            logger.error(
                "Failed to get messages for chat session session_id=%s",
                session_id, exc_info=True,
            )
            raise
        return [self._to_message_entity(m) for m in result.scalars().all()]

    @staticmethod
    def _to_session_entity(model: ChatSessionModel) -> ChatSession:
        return ChatSession(
            id=model.id,
            title=model.title,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def _to_message_entity(model: ChatMessageModel) -> Message:
        return Message(
            id=model.id,
            session_id=model.session_id,
            role=MessageRole(model.role),
            content=model.content,
            sources=model.sources or [],
            created_at=model.created_at,
        )
