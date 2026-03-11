from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.rag.services.rag_application_service import RAGApplicationService
from src.composition.rag_composition import build_rag_application_service
from src.db.deps import get_db


async def get_rag_service(
    db: AsyncSession = Depends(get_db),
) -> RAGApplicationService:
    return build_rag_application_service(db)
