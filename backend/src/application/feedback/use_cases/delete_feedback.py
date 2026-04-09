from src.domain.feedback.ports.feedback_repository import FeedbackRepository
from src.domain.shared.ports.unit_of_work import UnitOfWork


class DeleteFeedbackUseCase:
    """Deletes user feedback for a given target."""

    def __init__(
        self,
        feedback_repository: FeedbackRepository,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._feedback_repository = feedback_repository
        self._uow = unit_of_work

    async def execute(
        self, user_id: str, target_type: str, target_id: str,
    ) -> bool:
        async with self._uow:
            deleted = await self._feedback_repository.delete(
                user_id, target_type, target_id,
            )
        return deleted
