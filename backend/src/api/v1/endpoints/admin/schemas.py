from pydantic import BaseModel


class AdminUserResponse(BaseModel):
    id: str
    username: str
    profile_type: str | None
    created_at: str


class CreateUserRequest(BaseModel):
    username: str
    password: str
    profile_type: str | None = None


class UpdateUserRequest(BaseModel):
    password: str | None = None
    profile_type: str | None = None
