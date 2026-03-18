from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.search.services.search_application_service import (
    SearchApplicationService,
)
from src.composition.search_composition import (
    build_search_application_service,
)
from src.db.deps import get_db


async def get_search_service(
    db: AsyncSession = Depends(get_db),
) -> SearchApplicationService:
    return build_search_application_service(db)
