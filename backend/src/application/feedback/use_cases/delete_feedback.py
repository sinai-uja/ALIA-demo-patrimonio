from src.domain.feedback.ports.feedback_repository import FeedbackRepository


class DeleteFeedbackUseCase:
    """Deletes user feedback for a given target."""

    def __init__(self, feedback_repository: FeedbackRepository) -> None:
        self._feedback_repository = feedback_repository

    async def execute(
        self, user_id: str, target_type: str, target_id: str,
    ) -> bool:
        return await self._feedback_repository.delete(user_id, target_type, target_id)
