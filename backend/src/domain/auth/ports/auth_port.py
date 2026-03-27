import uuid
from abc import ABC, abstractmethod

from src.domain.auth.entities.user import User, UserProfileType


class AuthPort(ABC):
    @abstractmethod
    def authenticate(self, username: str, password: str) -> User | None: ...

    @abstractmethod
    def get_user_by_username(self, username: str) -> User | None: ...

    @abstractmethod
    def update_profile_type(self, user_id: uuid.UUID, profile_type_name: str) -> User: ...

    @abstractmethod
    def list_profile_types(self) -> list[UserProfileType]: ...
