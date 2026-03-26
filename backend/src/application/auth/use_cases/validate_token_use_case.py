from src.domain.auth.entities.user import User
from src.domain.auth.ports.token_port import TokenPort


class ValidateTokenUseCase:
    def __init__(self, token_port: TokenPort) -> None:
        self._token_port = token_port

    def execute(self, token: str) -> User:
        username = self._token_port.validate_token(token)
        if username is None:
            raise ValueError("Invalid token")
        return User(username=username)
