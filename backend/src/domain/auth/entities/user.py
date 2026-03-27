import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class UserProfileType:
    id: uuid.UUID
    name: str


@dataclass(frozen=True)
class User:
    id: uuid.UUID
    username: str
    password_hash: str
    profile_type: UserProfileType | None = None
