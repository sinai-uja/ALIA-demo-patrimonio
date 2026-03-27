from src.domain.feedback.ports.feedback_repository import FeedbackRepository


class GetFeedbackBatchUseCase:
    """Retrieves feedback values for multiple targets at once."""

    def __init__(self, feedback_repository: FeedbackRepository) -> None:
        self._feedback_repository = feedback_repository

    async def execute(
        self, user_id: str, target_type: str, target_ids: list[str],
    ) -> dict[str, int]:
        feedbacks = await self._feedback_repository.get_batch(
            user_id, target_type, target_ids,
        )
        return {fb.target_id: fb.value for fb in feedbacks}
