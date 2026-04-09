from src.application.auth.exceptions import InvalidTokenError
from src.domain.auth.entities.user import User
from src.domain.auth.ports.auth_port import AuthPort
from src.domain.auth.ports.token_port import TokenPort


class ValidateTokenUseCase:
    def __init__(self, token_port: TokenPort, auth_port: AuthPort) -> None:
        self._token_port = token_port
        self._auth_port = auth_port

    def execute(self, token: str) -> User:
        username = self._token_port.validate_token(token)
        if username is None:
            raise InvalidTokenError("Invalid token")
        user = self._auth_port.get_user_by_username(username)
        if user is None:
            raise InvalidTokenError("User not found")
        return user
