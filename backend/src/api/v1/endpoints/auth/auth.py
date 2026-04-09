import logging

from fastapi import APIRouter, Depends, Request

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
from src.application.auth.services.auth_application_service import (
    AuthApplicationService,
)
from src.config import settings
from src.domain.auth.entities.user import User

logger = logging.getLogger("iaph.auth")

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    raw_request: Request,
    service: AuthApplicationService = Depends(get_auth_service),
):
    client_ip = raw_request.client.host if raw_request.client else "unknown"
    logger.info("Login attempt: user=%r, ip=%s", request.username, client_ip)
    result = await service.login(
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


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: RefreshRequest,
    raw_request: Request,
    service: AuthApplicationService = Depends(get_auth_service),
):
    client_ip = raw_request.client.host if raw_request.client else "unknown"
    logger.info("Token refresh attempt: ip=%s", client_ip)
    result = await service.refresh(request.refresh_token)
    logger.info("Token refresh success: ip=%s", client_ip)
    return TokenResponse(
        access_token=result.access_token,
        refresh_token=result.refresh_token,
        token_type=result.token_type,
    )


@router.get("/me", response_model=UserInfoResponse)
async def get_me(
    user: User = Depends(get_current_user),
    service: AuthApplicationService = Depends(get_auth_service),
):
    info = service.get_user_info(user)
    return UserInfoResponse(
        id=info.id,
        username=info.username,
        profile_type=info.profile_type,
        is_root_admin=(info.username == settings.admin_username),
    )


@router.put("/profile-type", response_model=UserInfoResponse)
async def update_profile_type(
    request: UpdateProfileTypeRequest,
    user: User = Depends(get_current_user),
    service: AuthApplicationService = Depends(get_auth_service),
):
    info = await service.update_profile_type(user.id, request.profile_type)
    logger.info(
        "Profile type updated: user=%s profile_type=%s",
        user.username, request.profile_type,
    )
    return UserInfoResponse(id=info.id, username=info.username, profile_type=info.profile_type)


@router.get("/profile-types", response_model=list[ProfileTypeResponse])
async def list_profile_types(
    service: AuthApplicationService = Depends(get_auth_service),
):
    names = await service.list_profile_types()
    return [ProfileTypeResponse(name=n) for n in names if n != "admin"]
