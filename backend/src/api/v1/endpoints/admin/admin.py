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
from src.config import settings
from src.domain.auth.entities.user import User
from src.domain.auth.ports.auth_port import ProfileTypeInUseError

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
    try:
        pt = service.create_profile_type(CreateProfileTypeDTO(name=req.name))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return _to_pt_response(pt)


@router.put("/profile-types/{profile_type_id}", response_model=ProfileTypeResponse)
def rename_profile_type(
    profile_type_id: str,
    req: UpdateProfileTypeRequest,
    admin: User = Depends(get_current_admin),
    service=Depends(get_auth_service),
):
    existing = service.list_profile_types_admin()
    target = next((pt for pt in existing if pt.id == profile_type_id), None)
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tipo de perfil no encontrado"
        )
    if target.name == "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El perfil 'admin' no puede ser renombrado",
        )
    try:
        pt = service.rename_profile_type(
            UpdateProfileTypeDTO(profile_type_id=_uuid.UUID(profile_type_id), name=req.name)
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return _to_pt_response(pt)


@router.delete("/profile-types/{profile_type_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_profile_type(
    profile_type_id: str,
    admin: User = Depends(get_current_admin),
    service=Depends(get_auth_service),
):
    existing = service.list_profile_types_admin()
    target = next((pt for pt in existing if pt.id == profile_type_id), None)
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tipo de perfil no encontrado"
        )
    if target.name == "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El perfil 'admin' no puede ser eliminado",
        )
    try:
        service.delete_profile_type(_uuid.UUID(profile_type_id))
    except ProfileTypeInUseError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
