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
