import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status

from src.api.v1.endpoints.auth.deps import get_auth_service, get_current_user
from src.api.v1.endpoints.auth.schemas import (
    LoginRequest,
    ProfileTypeResponse,
    RefreshRequest,
    TokenResponse,
    UpdateProfileTypeRequest,
    UserInfoResponse,
)
from src.application.auth.dto.auth_dto import LoginDTO
from src.domain.auth.entities.user import User

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


@router.get("/me", response_model=UserInfoResponse)
def get_me(
    user: User = Depends(get_current_user),
    service=Depends(get_auth_service),
):
    info = service.get_user_info(user)
    return UserInfoResponse(id=info.id, username=info.username, profile_type=info.profile_type)


@router.put("/profile-type", response_model=UserInfoResponse)
def update_profile_type(
    request: UpdateProfileTypeRequest,
    user: User = Depends(get_current_user),
    service=Depends(get_auth_service),
):
    try:
        info = service.update_profile_type(user.id, request.profile_type)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    logger.info(
        "Profile type updated: user=%s profile_type=%s",
        user.username, request.profile_type,
    )
    return UserInfoResponse(id=info.id, username=info.username, profile_type=info.profile_type)


@router.get("/profile-types", response_model=list[ProfileTypeResponse])
def list_profile_types(service=Depends(get_auth_service)):
    names = service.list_profile_types()
    return [ProfileTypeResponse(name=n) for n in names]
