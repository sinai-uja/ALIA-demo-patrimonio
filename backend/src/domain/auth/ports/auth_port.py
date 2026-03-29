import uuid
from abc import ABC, abstractmethod

from src.domain.auth.entities.user import User, UserProfileType


class ProfileTypeInUseError(Exception):
    """Raised when trying to delete a profile type that has users assigned."""


class AuthPort(ABC):
    @abstractmethod
    def authenticate(self, username: str, password: str) -> User | None: ...

    @abstractmethod
    def get_user_by_username(self, username: str) -> User | None: ...

    @abstractmethod
    def update_profile_type(self, user_id: uuid.UUID, profile_type_name: str) -> User: ...

    @abstractmethod
    def list_profile_types(self) -> list[UserProfileType]: ...

    @abstractmethod
    def list_users(self) -> list[User]: ...

    @abstractmethod
    def get_user_by_id(self, user_id: uuid.UUID) -> User | None: ...

    @abstractmethod
    def create_user(
        self, username: str, password: str, profile_type_name: str | None,
    ) -> User: ...

    @abstractmethod
    def update_user(
        self,
        user_id: uuid.UUID,
        *,
        password: str | None,
        profile_type_name: str | None,
    ) -> User: ...

    @abstractmethod
    def delete_user(self, user_id: uuid.UUID) -> None: ...

    @abstractmethod
    def list_profile_types_with_counts(self) -> list[tuple[UserProfileType, int]]: ...

    @abstractmethod
    def create_profile_type(self, name: str) -> UserProfileType: ...

    @abstractmethod
    def rename_profile_type(self, profile_type_id: uuid.UUID, new_name: str) -> UserProfileType: ...

    @abstractmethod
    def delete_profile_type(self, profile_type_id: uuid.UUID) -> None: ...
