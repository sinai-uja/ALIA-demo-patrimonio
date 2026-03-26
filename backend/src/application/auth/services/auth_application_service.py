from src.application.auth.dto.auth_dto import LoginDTO, TokenPairDTO
from src.application.auth.use_cases.login_use_case import LoginUseCase
from src.application.auth.use_cases.refresh_token_use_case import (
    RefreshTokenUseCase,
)
from src.application.auth.use_cases.validate_token_use_case import (
    ValidateTokenUseCase,
)
from src.domain.auth.entities.user import User


class AuthApplicationService:
    def __init__(
        self,
        login_use_case: LoginUseCase,
        validate_token_use_case: ValidateTokenUseCase,
        refresh_token_use_case: RefreshTokenUseCase,
    ) -> None:
        self._login_use_case = login_use_case
        self._validate_token_use_case = validate_token_use_case
        self._refresh_token_use_case = refresh_token_use_case

    def login(self, dto: LoginDTO) -> TokenPairDTO:
        return self._login_use_case.execute(dto)

    def validate_token(self, token: str) -> User:
        return self._validate_token_use_case.execute(token)

    def refresh(self, refresh_token: str) -> TokenPairDTO:
        return self._refresh_token_use_case.execute(refresh_token)
