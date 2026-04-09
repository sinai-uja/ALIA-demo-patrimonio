import uuid as _uuid

from fastapi import APIRouter, Depends, HTTPException, status

from src.api.v1.endpoints.admin.schemas import (
    AdminUserResponse,
    CreateProfileTypeRequest,
    CreateUserRequest,
    ProfileTypeResponse,
    UpdateProfileTypeRequest,
    UpdateUserRequest,
)
from src.api.v1.endpoints.auth.deps import get_auth_service, get_current_user
from src.application.auth.dto.auth_dto import (
    CreateProfileTypeDTO,
    CreateUserDTO,
    UpdateProfileTypeDTO,
    UpdateUserDTO,
)
from src.application.auth.dto.user_dto import UserDTO
from src.domain.auth.entities.user import User

router = APIRouter(prefix="/admin", tags=["admin"])


def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    # Admin-access gate is a pure HTTP-layer authorization rule (who can hit
    # the admin router at all). Business-level rules live inside the use cases.
    if current_user.profile_type is None or current_user.profile_type.name != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


def _to_response(u: UserDTO) -> AdminUserResponse:
    return AdminUserResponse(
        id=u.id,
        username=u.username,
        profile_type=u.profile_type,
        created_at=u.created_at or "",
    )


@router.get("/users", response_model=list[AdminUserResponse])
def list_users(
    admin: User = Depends(get_current_admin),
    service=Depends(get_auth_service),
):
    return [_to_response(u) for u in service.list_users()]


@router.post(
    "/users",
    response_model=AdminUserResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_user(
    req: CreateUserRequest,
    admin: User = Depends(get_current_admin),
    service=Depends(get_auth_service),
):
    user = service.create_user(
        CreateUserDTO(
            username=req.username,
            password=req.password,
            profile_type_name=req.profile_type,
        ),
        actor=admin,
    )
    return _to_response(user)


@router.put("/users/{user_id}", response_model=AdminUserResponse)
def update_user(
    user_id: str,
    req: UpdateUserRequest,
    admin: User = Depends(get_current_admin),
    service=Depends(get_auth_service),
):
    uid = _uuid.UUID(user_id)
    user = service.update_user(
        UpdateUserDTO(
            user_id=uid,
            password=req.password,
            profile_type_name=req.profile_type,
        ),
        actor=admin,
    )
    return _to_response(user)


@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_user(
    user_id: str,
    admin: User = Depends(get_current_admin),
    service=Depends(get_auth_service),
):
    uid = _uuid.UUID(user_id)
    service.delete_user(uid, actor=admin)


def _to_pt_response(pt) -> ProfileTypeResponse:
    return ProfileTypeResponse(id=pt.id, name=pt.name, user_count=pt.user_count)


@router.get("/profile-types", response_model=list[ProfileTypeResponse])
def list_profile_types(
    admin: User = Depends(get_current_admin),
    service=Depends(get_auth_service),
):
    return [_to_pt_response(pt) for pt in service.list_profile_types_admin()]


@router.post(
    "/profile-types",
    response_model=ProfileTypeResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_profile_type(
    req: CreateProfileTypeRequest,
    admin: User = Depends(get_current_admin),
    service=Depends(get_auth_service),
):
    pt = service.create_profile_type(CreateProfileTypeDTO(name=req.name))
    return _to_pt_response(pt)


@router.put("/profile-types/{profile_type_id}", response_model=ProfileTypeResponse)
def rename_profile_type(
    profile_type_id: str,
    req: UpdateProfileTypeRequest,
    admin: User = Depends(get_current_admin),
    service=Depends(get_auth_service),
):
    pt = service.rename_profile_type(
        UpdateProfileTypeDTO(
            profile_type_id=_uuid.UUID(profile_type_id),
            name=req.name,
        )
    )
    return _to_pt_response(pt)


@router.delete("/profile-types/{profile_type_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_profile_type(
    profile_type_id: str,
    admin: User = Depends(get_current_admin),
    service=Depends(get_auth_service),
):
    service.delete_profile_type(_uuid.UUID(profile_type_id))
