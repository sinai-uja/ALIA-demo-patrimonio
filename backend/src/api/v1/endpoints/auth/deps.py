from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Depends, Header

from src.application.auth.exceptions import InvalidTokenError
from src.application.auth.services.auth_application_service import (
    AuthApplicationService,
)
from src.application.shared.exceptions import UnauthorizedActionError
from src.composition.auth_composition import build_auth_application_service
from src.composition.database import get_db
from src.domain.auth.entities.user import User

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def get_auth_service(
    db: AsyncSession = Depends(get_db),
) -> AuthApplicationService:
    return build_auth_application_service(db)


async def get_current_user(
    authorization: str = Header(...),
    service: AuthApplicationService = Depends(get_auth_service),
) -> User:
    if not authorization.startswith("Bearer "):
        raise InvalidTokenError("Token inválido")
    token = authorization.removeprefix("Bearer ")
    return await service.validate_token(token)


async def get_current_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    # Admin-access gate is a pure HTTP-layer authorization rule (who can hit
    # the admin router at all). Business-level rules live inside the use cases.
    if current_user.profile_type is None or current_user.profile_type.name != "admin":
        raise UnauthorizedActionError("Admin privileges required")
    return current_user
