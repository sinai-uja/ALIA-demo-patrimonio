import uuid

from src.application.auth.dto.auth_dto import (
    CreateUserDTO,
    LoginDTO,
    TokenPairDTO,
    UpdateUserDTO,
    UserInfoDTO,
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


class AuthApplicationService:
    def __init__(
        self,
        login_use_case: LoginUseCase,
        validate_token_use_case: ValidateTokenUseCase,
        refresh_token_use_case: RefreshTokenUseCase,
        auth_port: AuthPort,
    ) -> None:
        self._login_use_case = login_use_case
        self._validate_token_use_case = validate_token_use_case
        self._refresh_token_use_case = refresh_token_use_case
        self._auth_port = auth_port

    def login(self, dto: LoginDTO) -> TokenPairDTO:
        return self._login_use_case.execute(dto)

    def validate_token(self, token: str) -> User:
        return self._validate_token_use_case.execute(token)

    def refresh(self, refresh_token: str) -> TokenPairDTO:
        return self._refresh_token_use_case.execute(refresh_token)

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

    def list_users(self) -> list[UserInfoDTO]:
        users = self._auth_port.list_users()
        return [self.get_user_info(u) for u in users]

    def get_user_by_id(self, user_id: uuid.UUID) -> UserInfoDTO | None:
        user = self._auth_port.get_user_by_id(user_id)
        if user is None:
            return None
        return self.get_user_info(user)

    def create_user(self, dto: CreateUserDTO) -> UserInfoDTO:
        user = self._auth_port.create_user(
            username=dto.username,
            password=dto.password,
            profile_type_name=dto.profile_type_name,
        )
        return self.get_user_info(user)

    def update_user(self, dto: UpdateUserDTO) -> UserInfoDTO:
        user = self._auth_port.update_user(
            dto.user_id,
            password=dto.password,
            profile_type_name=dto.profile_type_name,
        )
        return self.get_user_info(user)

    def delete_user(self, user_id: uuid.UUID) -> None:
        self._auth_port.delete_user(user_id)
