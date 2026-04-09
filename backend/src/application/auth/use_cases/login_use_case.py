from src.application.auth.dto.auth_dto import LoginDTO, TokenPairDTO
from src.application.auth.exceptions import InvalidCredentialsError
from src.domain.auth.ports.auth_port import AuthPort
from src.domain.auth.ports.token_port import TokenPort


class LoginUseCase:
    def __init__(
        self, auth_port: AuthPort, token_port: TokenPort
    ) -> None:
        self._auth_port = auth_port
        self._token_port = token_port

    def execute(self, dto: LoginDTO) -> TokenPairDTO:
        user = self._auth_port.authenticate(dto.username, dto.password)
        if user is None:
            raise InvalidCredentialsError("Invalid credentials")
        return TokenPairDTO(
            access_token=self._token_port.create_access_token(
                user.username
            ),
            refresh_token=self._token_port.create_refresh_token(
                user.username
            ),
        )
