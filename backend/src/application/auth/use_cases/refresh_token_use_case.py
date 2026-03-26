from src.application.auth.dto.auth_dto import TokenPairDTO
from src.domain.auth.ports.token_port import TokenPort


class RefreshTokenUseCase:
    def __init__(self, token_port: TokenPort) -> None:
        self._token_port = token_port

    def execute(self, refresh_token: str) -> TokenPairDTO:
        username = self._token_port.validate_token(refresh_token)
        if username is None:
            raise ValueError("Invalid or expired refresh token")
        return TokenPairDTO(
            access_token=self._token_port.create_access_token(username),
            refresh_token=self._token_port.create_refresh_token(username),
        )
