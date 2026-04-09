from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.documents.services.documents_application_service import (
    DocumentsApplicationService,
)
from src.composition.documents_composition import build_documents_application_service
from src.composition.database import get_db


async def get_documents_service(
    db: AsyncSession = Depends(get_db),
) -> DocumentsApplicationService:
    return build_documents_application_service(db)
