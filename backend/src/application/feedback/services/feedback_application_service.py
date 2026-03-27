from src.application.feedback.dto.feedback_dto import FeedbackDTO, SubmitFeedbackDTO
from src.application.feedback.use_cases.delete_feedback import DeleteFeedbackUseCase
from src.application.feedback.use_cases.get_feedback import GetFeedbackUseCase
from src.application.feedback.use_cases.get_feedback_batch import GetFeedbackBatchUseCase
from src.application.feedback.use_cases.submit_feedback import SubmitFeedbackUseCase


class FeedbackApplicationService:
    """Application service that exposes feedback operations to the API layer."""

    def __init__(
        self,
        submit_feedback_use_case: SubmitFeedbackUseCase,
        delete_feedback_use_case: DeleteFeedbackUseCase,
        get_feedback_use_case: GetFeedbackUseCase,
        get_feedback_batch_use_case: GetFeedbackBatchUseCase,
    ) -> None:
        self._submit_feedback = submit_feedback_use_case
        self._delete_feedback = delete_feedback_use_case
        self._get_feedback = get_feedback_use_case
        self._get_feedback_batch = get_feedback_batch_use_case

    async def submit_feedback(
        self, user_id: str, dto: SubmitFeedbackDTO,
    ) -> FeedbackDTO:
        return await self._submit_feedback.execute(user_id, dto)

    async def delete_feedback(
        self, user_id: str, target_type: str, target_id: str,
    ) -> bool:
        return await self._delete_feedback.execute(user_id, target_type, target_id)

    async def get_feedback(
        self, user_id: str, target_type: str, target_id: str,
    ) -> FeedbackDTO | None:
        return await self._get_feedback.execute(user_id, target_type, target_id)

    async def get_feedback_batch(
        self, user_id: str, target_type: str, target_ids: list[str],
    ) -> dict[str, int]:
        return await self._get_feedback_batch.execute(user_id, target_type, target_ids)
