from src.application.feedback.dto.feedback_dto import FeedbackDTO
from src.domain.feedback.ports.feedback_repository import FeedbackRepository


class GetFeedbackUseCase:
    """Retrieves user feedback for a single target."""

    def __init__(self, feedback_repository: FeedbackRepository) -> None:
        self._feedback_repository = feedback_repository

    async def execute(
        self, user_id: str, target_type: str, target_id: str,
    ) -> FeedbackDTO | None:
        feedback = await self._feedback_repository.get(user_id, target_type, target_id)
        if feedback is None:
            return None
        return FeedbackDTO(
            id=str(feedback.id),
            user_id=feedback.user_id,
            target_type=feedback.target_type,
            target_id=feedback.target_id,
            value=feedback.value,
            created_at=feedback.created_at.isoformat(),
            updated_at=feedback.updated_at.isoformat(),
        )
