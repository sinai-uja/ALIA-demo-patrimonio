from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.feedback.services.feedback_application_service import (
    FeedbackApplicationService,
)
from src.composition.feedback_composition import build_feedback_application_service
from src.composition.database import get_db


async def get_feedback_service(
    db: AsyncSession = Depends(get_db),
) -> FeedbackApplicationService:
    return build_feedback_application_service(db)
