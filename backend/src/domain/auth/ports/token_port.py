from abc import ABC, abstractmethod


class TokenPort(ABC):
    @abstractmethod
    def create_access_token(self, username: str) -> str: ...

    @abstractmethod
    def create_refresh_token(self, username: str) -> str: ...

    @abstractmethod
    def validate_token(self, token: str) -> str | None: ...
