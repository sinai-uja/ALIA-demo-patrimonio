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
