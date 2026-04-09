import logging
from datetime import UTC, datetime
from uuid import uuid4

from src.application.feedback.dto.feedback_dto import FeedbackDTO, SubmitFeedbackDTO
from src.domain.feedback.entities.feedback import Feedback
from src.domain.feedback.ports.feedback_repository import FeedbackRepository
from src.domain.shared.ports.unit_of_work import UnitOfWork

logger = logging.getLogger("iaph.feedback")


class SubmitFeedbackUseCase:
    """Upserts user feedback for a given target."""

    def __init__(
        self,
        feedback_repository: FeedbackRepository,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._feedback_repository = feedback_repository
        self._uow = unit_of_work

    async def execute(self, user_id: str, dto: SubmitFeedbackDTO) -> FeedbackDTO:
        logger.info(
            "Feedback submitted: user=%s target_type=%s target_id=%s value=%d metadata=%s",
            user_id, dto.target_type, dto.target_id, dto.value, dto.metadata,
        )
        now = datetime.now(UTC)
        feedback = Feedback(
            id=uuid4(),
            user_id=user_id,
            target_type=dto.target_type,
            target_id=dto.target_id,
            value=dto.value,
            metadata=dto.metadata,
            created_at=now,
            updated_at=now,
        )
        async with self._uow:
            saved = await self._feedback_repository.upsert(feedback)
            result = FeedbackDTO(
                id=str(saved.id),
                user_id=saved.user_id,
                target_type=saved.target_type,
                target_id=saved.target_id,
                value=saved.value,
                created_at=saved.created_at.isoformat(),
                updated_at=saved.updated_at.isoformat(),
            )
        return result
