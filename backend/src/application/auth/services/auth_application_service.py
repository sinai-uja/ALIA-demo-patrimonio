import uuid

from src.application.auth.dto.auth_dto import (
    CreateProfileTypeDTO,
    CreateUserDTO,
    LoginDTO,
    ProfileTypeDTO,
    TokenPairDTO,
    UpdateProfileTypeDTO,
    UpdateUserDTO,
    UserInfoDTO,
)
from src.application.auth.dto.user_dto import UserDTO
from src.application.auth.exceptions import (
    AdminOnlyActionError,
    ProfileTypeProtectedError,
    RootAdminProtectedError,
    UserNotFoundError,
)
from src.application.auth.use_cases.ensure_root_admin import (
    EnsureRootAdminUseCase,
)
from src.application.auth.use_cases.login_use_case import LoginUseCase
from src.application.auth.use_cases.refresh_token_use_case import (
    RefreshTokenUseCase,
)
from src.application.auth.use_cases.validate_token_use_case import (
    ValidateTokenUseCase,
)
from src.domain.auth.entities.user import User
from src.domain.auth.ports.auth_port import AuthPort
from src.domain.shared.ports.unit_of_work import UnitOfWork

_ADMIN_PROFILE_NAME = "admin"


def _is_admin_actor(actor: User) -> bool:
    return actor.profile_type is not None and actor.profile_type.name == _ADMIN_PROFILE_NAME


class AuthApplicationService:
    def __init__(
        self,
        login_use_case: LoginUseCase,
        validate_token_use_case: ValidateTokenUseCase,
        refresh_token_use_case: RefreshTokenUseCase,
        ensure_root_admin_use_case: EnsureRootAdminUseCase,
        auth_port: AuthPort,
        unit_of_work: UnitOfWork,
        root_admin_username: str,
    ) -> None:
        self._login_use_case = login_use_case
        self._validate_token_use_case = validate_token_use_case
        self._refresh_token_use_case = refresh_token_use_case
        self._ensure_root_admin_use_case = ensure_root_admin_use_case
        self._auth_port = auth_port
        self._uow = unit_of_work
        self._root_admin_username = root_admin_username

    # ------------------------------------------------------------------ auth
    async def login(self, dto: LoginDTO) -> TokenPairDTO:
        return await self._login_use_case.execute(dto)

    async def validate_token(self, token: str) -> User:
        return await self._validate_token_use_case.execute(token)

    async def refresh(self, refresh_token: str) -> TokenPairDTO:
        return await self._refresh_token_use_case.execute(refresh_token)

    async def ensure_root_admin(self, username: str, password: str) -> None:
        await self._ensure_root_admin_use_case.execute(username, password)

    # --------------------------------------------------------------- profile
    def get_user_info(self, user: User) -> UserInfoDTO:
        return UserInfoDTO(
            id=str(user.id),
            username=user.username,
            profile_type=user.profile_type.name if user.profile_type else None,
            created_at=user.created_at.isoformat() if user.created_at else None,
        )

    async def update_profile_type(
        self, user_id: uuid.UUID, profile_type_name: str
    ) -> UserInfoDTO:
        async with self._uow:
            user = await self._auth_port.update_profile_type(
                user_id, profile_type_name
            )
            info = self.get_user_info(user)
        return info

    async def list_profile_types(self) -> list[str]:
        return [pt.name for pt in await self._auth_port.list_profile_types()]

    # --------------------------------------------------------- admin helpers
    def _is_root_username(self, username: str) -> bool:
        return username == self._root_admin_username

    def _to_user_dto(self, user: User) -> UserDTO:
        return UserDTO(
            id=str(user.id),
            username=user.username,
            profile_type=user.profile_type.name if user.profile_type else None,
            created_at=user.created_at.isoformat() if user.created_at else None,
        )

    # -------------------------------------------------------- admin use cases
    async def list_users(self) -> list[UserDTO]:
        return [self._to_user_dto(u) for u in await self._auth_port.list_users()]

    async def get_user_by_id(self, user_id: uuid.UUID) -> UserDTO | None:
        user = await self._auth_port.get_user_by_id(user_id)
        if user is None:
            return None
        return self._to_user_dto(user)

    async def create_user(self, dto: CreateUserDTO, *, actor: User) -> UserDTO:
        # Business rule: only the root admin can create other admin users.
        if (
            dto.profile_type_name == _ADMIN_PROFILE_NAME
            and not self._is_root_username(actor.username)
        ):
            raise AdminOnlyActionError(
                "Solo el administrador raíz puede crear otros administradores"
            )
        async with self._uow:
            user = await self._auth_port.create_user(
                username=dto.username,
                password=dto.password,
                profile_type_name=dto.profile_type_name,
            )
            result = self._to_user_dto(user)
        return result

    async def update_user(self, dto: UpdateUserDTO, *, actor: User) -> UserDTO:
        target = await self._auth_port.get_user_by_id(dto.user_id)
        if target is None:
            raise UserNotFoundError("User not found")

        # Business rule: the root admin record is immutable.
        if self._is_root_username(target.username):
            raise RootAdminProtectedError(
                "No se puede modificar el administrador raíz"
            )

        # Business rule: only the root admin can assign the admin profile.
        if (
            dto.profile_type_name == _ADMIN_PROFILE_NAME
            and not self._is_root_username(actor.username)
        ):
            raise AdminOnlyActionError(
                "Solo el administrador raíz puede asignar el perfil admin"
            )

        async with self._uow:
            user = await self._auth_port.update_user(
                dto.user_id,
                password=dto.password,
                profile_type_name=dto.profile_type_name,
            )
            result = self._to_user_dto(user)
        return result

    async def delete_user(self, user_id: uuid.UUID, *, actor: User) -> None:
        target = await self._auth_port.get_user_by_id(user_id)
        if target is None:
            raise UserNotFoundError("User not found")

        # Business rule: the root admin can never be deleted.
        if self._is_root_username(target.username):
            raise RootAdminProtectedError(
                "No se puede eliminar el administrador raíz"
            )

        # Business rule: only the root admin can delete other admin users.
        target_is_admin = (
            target.profile_type is not None
            and target.profile_type.name == _ADMIN_PROFILE_NAME
        )
        if target_is_admin and not self._is_root_username(actor.username):
            raise AdminOnlyActionError(
                "Solo el administrador raíz puede eliminar otros administradores"
            )

        async with self._uow:
            await self._auth_port.delete_user(user_id)

    # ---------------------------------------------------- profile type admin
    async def list_profile_types_admin(self) -> list[ProfileTypeDTO]:
        return [
            ProfileTypeDTO(id=str(pt.id), name=pt.name, user_count=count)
            for pt, count in await self._auth_port.list_profile_types_with_counts()
        ]

    async def create_profile_type(
        self, dto: CreateProfileTypeDTO
    ) -> ProfileTypeDTO:
        async with self._uow:
            pt = await self._auth_port.create_profile_type(dto.name)
            result = ProfileTypeDTO(id=str(pt.id), name=pt.name, user_count=0)
        return result

    async def rename_profile_type(
        self, dto: UpdateProfileTypeDTO
    ) -> ProfileTypeDTO:
        # Business rule: the 'admin' profile type cannot be renamed.
        existing = await self._auth_port.list_profile_types_with_counts()
        target = next(
            (pt for pt, _ in existing if pt.id == dto.profile_type_id), None
        )
        if target is None:
            from src.application.auth.exceptions import ProfileTypeNotFoundError

            raise ProfileTypeNotFoundError("Tipo de perfil no encontrado")
        if target.name == _ADMIN_PROFILE_NAME:
            raise ProfileTypeProtectedError(
                "El perfil 'admin' no puede ser renombrado"
            )

        async with self._uow:
            pt = await self._auth_port.rename_profile_type(
                dto.profile_type_id, dto.name
            )
            result = ProfileTypeDTO(id=str(pt.id), name=pt.name, user_count=0)
        return result

    async def delete_profile_type(self, profile_type_id: uuid.UUID) -> None:
        # Business rule: the 'admin' profile type cannot be deleted.
        existing = await self._auth_port.list_profile_types_with_counts()
        target = next(
            (pt for pt, _ in existing if pt.id == profile_type_id), None
        )
        if target is None:
            from src.application.auth.exceptions import ProfileTypeNotFoundError

            raise ProfileTypeNotFoundError("Tipo de perfil no encontrado")
        if target.name == _ADMIN_PROFILE_NAME:
            raise ProfileTypeProtectedError(
                "El perfil 'admin' no puede ser eliminado"
            )

        async with self._uow:
            await self._auth_port.delete_profile_type(profile_type_id)
