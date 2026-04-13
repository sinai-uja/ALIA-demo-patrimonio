from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Depends

from src.application.rag.services.rag_application_service import RAGApplicationService
from src.composition.database import get_db
from src.composition.rag_composition import build_rag_application_service

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def get_rag_service(
    db: AsyncSession = Depends(get_db),
) -> RAGApplicationService:
    return build_rag_application_service(db)
