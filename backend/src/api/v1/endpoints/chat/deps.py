from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.chat.services.chat_application_service import ChatApplicationService
from src.composition.chat_composition import build_chat_application_service
from src.composition.database import get_db


async def get_chat_service(
    db: AsyncSession = Depends(get_db),
) -> ChatApplicationService:
    return build_chat_application_service(db)
