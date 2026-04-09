from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Depends

from src.application.search.services.search_application_service import (
    SearchApplicationService,
)
from src.composition.search_composition import (
    build_search_application_service,
)
from src.composition.database import get_db

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def get_search_service(
    db: AsyncSession = Depends(get_db),
) -> SearchApplicationService:
    return build_search_application_service(db)
