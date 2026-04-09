from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Depends

from src.application.chat.services.chat_application_service import ChatApplicationService
from src.composition.chat_composition import build_chat_application_service
from src.composition.database import get_db

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def get_chat_service(
    db: AsyncSession = Depends(get_db),
) -> ChatApplicationService:
    return build_chat_application_service(db)
