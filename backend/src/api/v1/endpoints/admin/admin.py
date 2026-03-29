import uuid as _uuid

from fastapi import APIRouter, Depends, HTTPException, status

from src.api.v1.endpoints.admin.schemas import (
    AdminUserResponse,
    CreateUserRequest,
    UpdateUserRequest,
)
from src.api.v1.endpoints.auth.deps import get_auth_service, get_current_user
from src.application.auth.dto.auth_dto import CreateUserDTO, UpdateUserDTO
from src.config import settings
from src.domain.auth.entities.user import User

router = APIRouter(prefix="/admin", tags=["admin"])


def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.profile_type is None or current_user.profile_type.name != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


def _is_root(username: str) -> bool:
    return username == settings.admin_username


def _to_response(u) -> AdminUserResponse:
    return AdminUserResponse(
        id=str(u.id),
        username=u.username,
        profile_type=u.profile_type,
        created_at=u.created_at or "",
    )


@router.get("/users", response_model=list[AdminUserResponse])
def list_users(
    admin: User = Depends(get_current_admin),
    service=Depends(get_auth_service),
):
    users = service.list_users()
    return [_to_response(u) for u in users]


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
    if req.profile_type == "admin" and not _is_root(admin.username):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el administrador raíz puede crear otros administradores",
        )
    try:
        user = service.create_user(
            CreateUserDTO(
                username=req.username,
                password=req.password,
                profile_type_name=req.profile_type,
            )
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
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
    target = service.get_user_by_id(uid)
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    if _is_root(target.username):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No se puede modificar el administrador raíz",
        )
    if req.profile_type == "admin" and not _is_root(admin.username):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el administrador raíz puede asignar el perfil admin",
        )
    try:
        user = service.update_user(
            UpdateUserDTO(
                user_id=uid,
                password=req.password,
                profile_type_name=req.profile_type,
            )
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
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
    target = service.get_user_by_id(uid)
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    if _is_root(target.username):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No se puede eliminar el administrador raíz",
        )
    if target.profile_type == "admin" and not _is_root(admin.username):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el administrador raíz puede eliminar otros administradores",
        )
    service.delete_user(uid)
