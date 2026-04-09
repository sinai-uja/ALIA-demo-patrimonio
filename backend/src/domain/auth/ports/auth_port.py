import uuid
from abc import ABC, abstractmethod

from src.domain.auth.entities.user import User, UserProfileType


class AuthPort(ABC):
    @abstractmethod
    async def authenticate(self, username: str, password: str) -> User | None: ...

    @abstractmethod
    async def get_user_by_username(self, username: str) -> User | None: ...

    @abstractmethod
    async def update_profile_type(
        self, user_id: uuid.UUID, profile_type_name: str
    ) -> User: ...

    @abstractmethod
    async def list_profile_types(self) -> list[UserProfileType]: ...

    @abstractmethod
    async def list_users(self) -> list[User]: ...

    @abstractmethod
    async def get_user_by_id(self, user_id: uuid.UUID) -> User | None: ...

    @abstractmethod
    async def create_user(
        self, username: str, password: str, profile_type_name: str | None,
    ) -> User: ...

    @abstractmethod
    async def update_user(
        self,
        user_id: uuid.UUID,
        *,
        password: str | None,
        profile_type_name: str | None,
    ) -> User: ...

    @abstractmethod
    async def delete_user(self, user_id: uuid.UUID) -> None: ...

    @abstractmethod
    async def list_profile_types_with_counts(
        self,
    ) -> list[tuple[UserProfileType, int]]: ...

    @abstractmethod
    async def create_profile_type(self, name: str) -> UserProfileType: ...

    @abstractmethod
    async def rename_profile_type(
        self, profile_type_id: uuid.UUID, new_name: str
    ) -> UserProfileType: ...

    @abstractmethod
    async def delete_profile_type(self, profile_type_id: uuid.UUID) -> None: ...
