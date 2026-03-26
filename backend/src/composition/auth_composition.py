from src.application.auth.services.auth_application_service import (
    AuthApplicationService,
)
from src.application.auth.use_cases.login_use_case import LoginUseCase
from src.application.auth.use_cases.refresh_token_use_case import (
    RefreshTokenUseCase,
)
from src.application.auth.use_cases.validate_token_use_case import (
    ValidateTokenUseCase,
)
from src.config import settings
from src.infrastructure.auth.adapters.hardcoded_auth_adapter import (
    HardcodedAuthAdapter,
)
from src.infrastructure.auth.adapters.jwt_token_adapter import (
    JWTTokenAdapter,
)


def build_auth_application_service() -> AuthApplicationService:
    auth_adapter = HardcodedAuthAdapter(
        settings.auth_username, settings.auth_password
    )
    token_adapter = JWTTokenAdapter(
        secret_key=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
        access_expire_minutes=settings.jwt_access_token_expire_minutes,
        refresh_expire_days=settings.jwt_refresh_token_expire_days,
    )
    return AuthApplicationService(
        login_use_case=LoginUseCase(
            auth_port=auth_adapter, token_port=token_adapter
        ),
        validate_token_use_case=ValidateTokenUseCase(
            token_port=token_adapter
        ),
        refresh_token_use_case=RefreshTokenUseCase(
            token_port=token_adapter
        ),
    )
