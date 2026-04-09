from fastapi import Header

from src.application.auth.exceptions import InvalidTokenError
from src.application.auth.services.auth_application_service import (
    AuthApplicationService,
)
from src.composition.auth_composition import build_auth_application_service
from src.domain.auth.entities.user import User


def get_auth_service() -> AuthApplicationService:
    return build_auth_application_service()


def get_current_user(authorization: str = Header(...)) -> User:
    if not authorization.startswith("Bearer "):
        raise InvalidTokenError("Token inválido")
    token = authorization.removeprefix("Bearer ")
    service = build_auth_application_service()
    return service.validate_token(token)
