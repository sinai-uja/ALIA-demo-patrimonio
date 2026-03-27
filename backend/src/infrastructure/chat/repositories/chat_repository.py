import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.chat.entities.chat_session import ChatSession
from src.domain.chat.entities.message import Message
from src.domain.chat.entities.message_role import MessageRole
from src.domain.chat.ports.chat_repository import ChatRepository
from src.infrastructure.chat.models import ChatMessageModel, ChatSessionModel


class ChatRepositoryImpl(ChatRepository):
    """Async SQLAlchemy implementation of the ChatRepository port."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create_session(
        self, title: str, user_id: uuid.UUID | None = None,
    ) -> ChatSession:
        model = ChatSessionModel(id=uuid.uuid4(), title=title, user_id=user_id)
        self._db.add(model)
        await self._db.commit()
        await self._db.refresh(model)
        return self._to_session_entity(model)

    async def get_session(
        self, session_id: uuid.UUID, user_id: uuid.UUID | None = None,
    ) -> ChatSession | None:
        stmt = select(ChatSessionModel).where(ChatSessionModel.id == session_id)
        if user_id is not None:
            stmt = stmt.where(ChatSessionModel.user_id == user_id)
        result = await self._db.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._to_session_entity(model)

    async def list_sessions(self, user_id: uuid.UUID | None = None) -> list[ChatSession]:
        stmt = select(ChatSessionModel).order_by(ChatSessionModel.updated_at.desc())
        if user_id is not None:
            stmt = stmt.where(ChatSessionModel.user_id == user_id)
        result = await self._db.execute(stmt)
        return [self._to_session_entity(m) for m in result.scalars().all()]

    async def delete_session(
        self, session_id: uuid.UUID, user_id: uuid.UUID | None = None,
    ) -> None:
        stmt = delete(ChatSessionModel).where(ChatSessionModel.id == session_id)
        if user_id is not None:
            stmt = stmt.where(ChatSessionModel.user_id == user_id)
        await self._db.execute(stmt)
        await self._db.commit()

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
        await self._db.execute(stmt)
        await self._db.commit()

        get_stmt = select(ChatSessionModel).where(ChatSessionModel.id == session_id)
        if user_id is not None:
            get_stmt = get_stmt.where(ChatSessionModel.user_id == user_id)
        result = await self._db.execute(get_stmt)
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

        # Update session updated_at
        await self._db.execute(
            update(ChatSessionModel)
            .where(ChatSessionModel.id == session_id)
            .values(updated_at=datetime.now(UTC))
        )

        await self._db.commit()
        await self._db.refresh(model)
        return self._to_message_entity(model)

    async def get_messages(self, session_id: uuid.UUID) -> list[Message]:
        result = await self._db.execute(
            select(ChatMessageModel)
            .where(ChatMessageModel.session_id == session_id)
            .order_by(ChatMessageModel.created_at.asc())
        )
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
