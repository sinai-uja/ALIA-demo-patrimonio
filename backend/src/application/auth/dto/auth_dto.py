import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class LoginDTO:
    username: str
    password: str


@dataclass(frozen=True)
class TokenPairDTO:
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


@dataclass(frozen=True)
class UserInfoDTO:
    id: str
    username: str
    profile_type: str | None = None
    created_at: str | None = None


@dataclass(frozen=True)
class CreateUserDTO:
    username: str
    password: str
    profile_type_name: str | None = None


@dataclass(frozen=True)
class UpdateUserDTO:
    user_id: uuid.UUID
    password: str | None = None
    profile_type_name: str | None = None


@dataclass(frozen=True)
class ProfileTypeDTO:
    id: str
    name: str
    user_count: int


@dataclass(frozen=True)
class CreateProfileTypeDTO:
    name: str


@dataclass(frozen=True)
class UpdateProfileTypeDTO:
    profile_type_id: uuid.UUID
    name: str
