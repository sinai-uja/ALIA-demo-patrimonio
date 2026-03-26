from abc import ABC, abstractmethod

from src.domain.auth.entities.user import User


class AuthPort(ABC):
    @abstractmethod
    def authenticate(self, username: str, password: str) -> User | None: ...
