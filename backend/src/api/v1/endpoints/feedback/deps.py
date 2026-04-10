from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Depends

from src.application.feedback.services.feedback_application_service import (
    FeedbackApplicationService,
)
from src.composition.database import get_db
from src.composition.feedback_composition import build_feedback_application_service

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def get_feedback_service(
    db: AsyncSession = Depends(get_db),
) -> FeedbackApplicationService:
    return build_feedback_application_service(db)
