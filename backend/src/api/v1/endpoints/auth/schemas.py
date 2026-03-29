from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class UserInfoResponse(BaseModel):
    id: str
    username: str
    profile_type: str | None = None
    is_root_admin: bool = False


class UpdateProfileTypeRequest(BaseModel):
    profile_type: str


class ProfileTypeResponse(BaseModel):
    name: str
