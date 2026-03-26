import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status

from src.api.v1.endpoints.auth.deps import get_auth_service
from src.api.v1.endpoints.auth.schemas import (
    LoginRequest,
    RefreshRequest,
    TokenResponse,
)
from src.application.auth.dto.auth_dto import LoginDTO

logger = logging.getLogger("iaph.auth")

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
def login(
    request: LoginRequest,
    raw_request: Request,
    service=Depends(get_auth_service),
):
    client_ip = raw_request.client.host if raw_request.client else "unknown"
    logger.info("Login attempt: user=%r, ip=%s", request.username, client_ip)
    try:
        result = service.login(
            LoginDTO(
                username=request.username,
                password=request.password,
            )
        )
        logger.info("Login success: user=%r, ip=%s", request.username, client_ip)
        return TokenResponse(
            access_token=result.access_token,
            refresh_token=result.refresh_token,
            token_type=result.token_type,
        )
    except ValueError:
        logger.warning("Login failed: user=%r, ip=%s", request.username, client_ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
        )


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    request: RefreshRequest,
    raw_request: Request,
    service=Depends(get_auth_service),
):
    client_ip = raw_request.client.host if raw_request.client else "unknown"
    logger.info("Token refresh attempt: ip=%s", client_ip)
    try:
        result = service.refresh(request.refresh_token)
        logger.info("Token refresh success: ip=%s", client_ip)
        return TokenResponse(
            access_token=result.access_token,
            refresh_token=result.refresh_token,
            token_type=result.token_type,
        )
    except ValueError:
        logger.warning("Token refresh failed: ip=%s", client_ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de refresco inválido o expirado",
        )
