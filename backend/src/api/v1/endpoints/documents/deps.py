from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Depends

from src.application.documents.services.documents_application_service import (
    DocumentsApplicationService,
)
from src.composition.database import get_db
from src.composition.documents_composition import build_documents_application_service

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def get_documents_service(
    db: AsyncSession = Depends(get_db),
) -> DocumentsApplicationService:
    return build_documents_application_service(db)
