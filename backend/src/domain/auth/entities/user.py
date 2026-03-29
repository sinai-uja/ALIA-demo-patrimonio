import uuid
from dataclasses import dataclass
from datetime import datetime


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
    created_at: datetime | None = None
