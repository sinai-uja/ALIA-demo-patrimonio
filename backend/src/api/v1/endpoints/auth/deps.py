from fastapi import Header, HTTPException, status

from src.application.auth.services.auth_application_service import (
    AuthApplicationService,
)
from src.composition.auth_composition import build_auth_application_service
from src.domain.auth.entities.user import User


def get_auth_service() -> AuthApplicationService:
    return build_auth_application_service()


def get_current_user(authorization: str = Header(...)) -> User:
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = authorization.removeprefix("Bearer ")
    service = build_auth_application_service()
    try:
        return service.validate_token(token)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
