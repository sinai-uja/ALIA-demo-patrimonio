from sqlalchemy import and_, delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.feedback.entities.feedback import Feedback
from src.domain.feedback.ports.feedback_repository import FeedbackRepository
from src.infrastructure.feedback.models import UserFeedbackModel


class SqlAlchemyFeedbackRepository(FeedbackRepository):
    """Async SQLAlchemy implementation of the FeedbackRepository port."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def upsert(self, feedback: Feedback) -> Feedback:
        table = UserFeedbackModel.__table__
        stmt = insert(table).values(
            id=feedback.id,
            user_id=feedback.user_id,
            target_type=feedback.target_type,
            target_id=feedback.target_id,
            value=feedback.value,
            metadata=feedback.metadata,
            created_at=feedback.created_at,
            updated_at=feedback.updated_at,
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uq_user_feedback_user_target",
            set_={
                "value": stmt.excluded.value,
                "metadata": stmt.excluded.metadata,
                "updated_at": stmt.excluded.updated_at,
            },
        )
        await self._db.execute(stmt)
        await self._db.commit()

        row = await self.get(
            feedback.user_id, feedback.target_type, feedback.target_id,
        )
        return row  # type: ignore[return-value]

    async def delete(
        self, user_id: str, target_type: str, target_id: str,
    ) -> bool:
        stmt = (
            delete(UserFeedbackModel)
            .where(
                and_(
                    UserFeedbackModel.user_id == user_id,
                    UserFeedbackModel.target_type == target_type,
                    UserFeedbackModel.target_id == target_id,
                ),
            )
        )
        result = await self._db.execute(stmt)
        await self._db.commit()
        return result.rowcount > 0

    async def get(
        self, user_id: str, target_type: str, target_id: str,
    ) -> Feedback | None:
        stmt = select(UserFeedbackModel).where(
            and_(
                UserFeedbackModel.user_id == user_id,
                UserFeedbackModel.target_type == target_type,
                UserFeedbackModel.target_id == target_id,
            ),
        )
        result = await self._db.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._model_to_entity(model)

    async def get_batch(
        self, user_id: str, target_type: str, target_ids: list[str],
    ) -> list[Feedback]:
        if not target_ids:
            return []
        stmt = select(UserFeedbackModel).where(
            and_(
                UserFeedbackModel.user_id == user_id,
                UserFeedbackModel.target_type == target_type,
                UserFeedbackModel.target_id.in_(target_ids),
            ),
        )
        result = await self._db.execute(stmt)
        models = result.scalars().all()
        return [self._model_to_entity(m) for m in models]

    def _model_to_entity(self, model: UserFeedbackModel) -> Feedback:
        """Map a SQLAlchemy model instance to a Feedback entity."""
        return Feedback(
            id=model.id,
            user_id=model.user_id,
            target_type=model.target_type,
            target_id=model.target_id,
            value=model.value,
            metadata=model.metadata_,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
