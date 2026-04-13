from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Depends

from src.application.heritage.services.heritage_application_service import (
    HeritageApplicationService,
)
from src.composition.database import get_db
from src.composition.heritage_composition import (
    build_heritage_application_service,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def get_heritage_service(
    db: AsyncSession = Depends(get_db),
) -> HeritageApplicationService:
    return build_heritage_application_service(db)
