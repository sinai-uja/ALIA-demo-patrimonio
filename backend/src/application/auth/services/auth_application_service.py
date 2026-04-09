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
        root_admin_username: str,
    ) -> None:
        self._login_use_case = login_use_case
        self._validate_token_use_case = validate_token_use_case
        self._refresh_token_use_case = refresh_token_use_case
        self._ensure_root_admin_use_case = ensure_root_admin_use_case
        self._auth_port = auth_port
        self._root_admin_username = root_admin_username

    # ------------------------------------------------------------------ auth
    def login(self, dto: LoginDTO) -> TokenPairDTO:
        return self._login_use_case.execute(dto)

    def validate_token(self, token: str) -> User:
        return self._validate_token_use_case.execute(token)

    def refresh(self, refresh_token: str) -> TokenPairDTO:
        return self._refresh_token_use_case.execute(refresh_token)

    def ensure_root_admin(self, username: str, password: str) -> None:
        self._ensure_root_admin_use_case.execute(username, password)

    # --------------------------------------------------------------- profile
    def get_user_info(self, user: User) -> UserInfoDTO:
        return UserInfoDTO(
            id=str(user.id),
            username=user.username,
            profile_type=user.profile_type.name if user.profile_type else None,
            created_at=user.created_at.isoformat() if user.created_at else None,
        )

    def update_profile_type(self, user_id: uuid.UUID, profile_type_name: str) -> UserInfoDTO:
        user = self._auth_port.update_profile_type(user_id, profile_type_name)
        return self.get_user_info(user)

    def list_profile_types(self) -> list[str]:
        return [pt.name for pt in self._auth_port.list_profile_types()]

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
    def list_users(self) -> list[UserDTO]:
        return [self._to_user_dto(u) for u in self._auth_port.list_users()]

    def get_user_by_id(self, user_id: uuid.UUID) -> UserDTO | None:
        user = self._auth_port.get_user_by_id(user_id)
        if user is None:
            return None
        return self._to_user_dto(user)

    def create_user(self, dto: CreateUserDTO, *, actor: User) -> UserDTO:
        # Business rule: only the root admin can create other admin users.
        if (
            dto.profile_type_name == _ADMIN_PROFILE_NAME
            and not self._is_root_username(actor.username)
        ):
            raise AdminOnlyActionError(
                "Solo el administrador raíz puede crear otros administradores"
            )
        user = self._auth_port.create_user(
            username=dto.username,
            password=dto.password,
            profile_type_name=dto.profile_type_name,
        )
        return self._to_user_dto(user)

    def update_user(self, dto: UpdateUserDTO, *, actor: User) -> UserDTO:
        target = self._auth_port.get_user_by_id(dto.user_id)
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

        user = self._auth_port.update_user(
            dto.user_id,
            password=dto.password,
            profile_type_name=dto.profile_type_name,
        )
        return self._to_user_dto(user)

    def delete_user(self, user_id: uuid.UUID, *, actor: User) -> None:
        target = self._auth_port.get_user_by_id(user_id)
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

        self._auth_port.delete_user(user_id)

    # ---------------------------------------------------- profile type admin
    def list_profile_types_admin(self) -> list[ProfileTypeDTO]:
        return [
            ProfileTypeDTO(id=str(pt.id), name=pt.name, user_count=count)
            for pt, count in self._auth_port.list_profile_types_with_counts()
        ]

    def create_profile_type(self, dto: CreateProfileTypeDTO) -> ProfileTypeDTO:
        pt = self._auth_port.create_profile_type(dto.name)
        return ProfileTypeDTO(id=str(pt.id), name=pt.name, user_count=0)

    def rename_profile_type(self, dto: UpdateProfileTypeDTO) -> ProfileTypeDTO:
        # Business rule: the 'admin' profile type cannot be renamed.
        existing = self._auth_port.list_profile_types_with_counts()
        target = next((pt for pt, _ in existing if pt.id == dto.profile_type_id), None)
        if target is None:
            from src.application.auth.exceptions import ProfileTypeNotFoundError

            raise ProfileTypeNotFoundError("Tipo de perfil no encontrado")
        if target.name == _ADMIN_PROFILE_NAME:
            raise ProfileTypeProtectedError(
                "El perfil 'admin' no puede ser renombrado"
            )

        pt = self._auth_port.rename_profile_type(dto.profile_type_id, dto.name)
        return ProfileTypeDTO(id=str(pt.id), name=pt.name, user_count=0)

    def delete_profile_type(self, profile_type_id: uuid.UUID) -> None:
        # Business rule: the 'admin' profile type cannot be deleted.
        existing = self._auth_port.list_profile_types_with_counts()
        target = next((pt for pt, _ in existing if pt.id == profile_type_id), None)
        if target is None:
            from src.application.auth.exceptions import ProfileTypeNotFoundError

            raise ProfileTypeNotFoundError("Tipo de perfil no encontrado")
        if target.name == _ADMIN_PROFILE_NAME:
            raise ProfileTypeProtectedError(
                "El perfil 'admin' no puede ser eliminado"
            )

        self._auth_port.delete_profile_type(profile_type_id)
