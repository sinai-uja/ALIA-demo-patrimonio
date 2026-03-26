from src.domain.auth.entities.user import User
from src.domain.auth.ports.auth_port import AuthPort


class HardcodedAuthAdapter(AuthPort):
    def __init__(self, username: str, password: str) -> None:
        self._username = username
        self._password = password

    def authenticate(self, username: str, password: str) -> User | None:
        if username == self._username and password == self._password:
            return User(username=username)
        return None
