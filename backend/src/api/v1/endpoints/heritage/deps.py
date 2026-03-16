from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.heritage.services.heritage_application_service import (
    HeritageApplicationService,
)
from src.composition.heritage_composition import (
    build_heritage_application_service,
)
from src.db.deps import get_db


async def get_heritage_service(
    db: AsyncSession = Depends(get_db),
) -> HeritageApplicationService:
    return build_heritage_application_service(db)
