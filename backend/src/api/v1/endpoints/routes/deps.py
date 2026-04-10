from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Depends

from src.application.routes.services.routes_application_service import (
    RoutesApplicationService,
)
from src.composition.routes_composition import build_routes_application_service
from src.composition.database import get_db

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def get_routes_service(
    db: AsyncSession = Depends(get_db),
) -> RoutesApplicationService:
    return build_routes_application_service(db)
