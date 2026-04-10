from sqlalchemy.ext.asyncio import AsyncSession

from src.application.feedback.services.feedback_application_service import (
    FeedbackApplicationService,
)
from src.application.feedback.use_cases.delete_feedback import DeleteFeedbackUseCase
from src.application.feedback.use_cases.get_feedback import GetFeedbackUseCase
from src.application.feedback.use_cases.get_feedback_batch import (
    GetFeedbackBatchUseCase,
)
from src.application.feedback.use_cases.submit_feedback import SubmitFeedbackUseCase
from src.infrastructure.feedback.repositories.feedback_repository import (
    SqlAlchemyFeedbackRepository,
)
from src.infrastructure.shared.adapters.sqlalchemy_unit_of_work import (
    SqlAlchemyUnitOfWork,
)


def build_feedback_application_service(
    db: AsyncSession,
) -> FeedbackApplicationService:
    """Wire all feedback adapters and return the application service."""
    feedback_repository = SqlAlchemyFeedbackRepository(db)
    uow = SqlAlchemyUnitOfWork(session=db)

    submit_feedback_use_case = SubmitFeedbackUseCase(
        feedback_repository=feedback_repository,
        unit_of_work=uow,
    )
    delete_feedback_use_case = DeleteFeedbackUseCase(
        feedback_repository=feedback_repository,
        unit_of_work=uow,
    )
    get_feedback_use_case = GetFeedbackUseCase(
        feedback_repository=feedback_repository,
    )
    get_feedback_batch_use_case = GetFeedbackBatchUseCase(
        feedback_repository=feedback_repository,
    )

    return FeedbackApplicationService(
        submit_feedback_use_case=submit_feedback_use_case,
        delete_feedback_use_case=delete_feedback_use_case,
        get_feedback_use_case=get_feedback_use_case,
        get_feedback_batch_use_case=get_feedback_batch_use_case,
    )
