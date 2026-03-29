import re

from pydantic import BaseModel, field_validator
from pydantic_core import PydanticCustomError

_USERNAME_RE = re.compile(r"^[a-zA-Z0-9_\-\.@]+$")
_PASSWORD_RE = re.compile(r"^[a-zA-Z0-9_\-\.@!#$%&*+=?]+$")


class AdminUserResponse(BaseModel):
    id: str
    username: str
    profile_type: str | None
    created_at: str


class CreateUserRequest(BaseModel):
    username: str
    password: str
    profile_type: str | None = None

    @field_validator("username", mode="before")
    @classmethod
    def validate_username(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise PydanticCustomError(
                "validation_error", "El nombre de usuario no puede estar vacío"
            )
        if len(v) < 3:
            raise PydanticCustomError(
                "validation_error", "El nombre de usuario debe tener al menos 3 caracteres"
            )
        if len(v) > 64:
            raise PydanticCustomError(
                "validation_error", "El nombre de usuario no puede superar los 64 caracteres"
            )
        if not _USERNAME_RE.match(v):
            raise PydanticCustomError(
                "validation_error",
                "El nombre de usuario solo puede contener letras, números y los símbolos _ - . @",
            )
        return v

    @field_validator("password", mode="before")
    @classmethod
    def validate_password(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise PydanticCustomError("validation_error", "La contraseña no puede estar vacía")
        if len(v) < 6:
            raise PydanticCustomError(
                "validation_error", "La contraseña debe tener al menos 6 caracteres"
            )
        if len(v) > 128:
            raise PydanticCustomError(
                "validation_error", "La contraseña no puede superar los 128 caracteres"
            )
        if not _PASSWORD_RE.match(v):
            raise PydanticCustomError(
                "validation_error",
                "La contraseña solo puede contener letras, números"
                " y los símbolos _ - . @ ! # $ % & * + = ?",
            )
        return v


def _validate_pt_name(v: str) -> str:
    v = v.strip()
    if not v:
        raise PydanticCustomError("validation_error", "El nombre no puede estar vacío")
    if len(v) < 2:
        raise PydanticCustomError("validation_error", "El nombre debe tener al menos 2 caracteres")
    if len(v) > 64:
        raise PydanticCustomError(
            "validation_error", "El nombre no puede superar los 64 caracteres"
        )
    if not _USERNAME_RE.match(v):
        raise PydanticCustomError(
            "validation_error",
            "El nombre solo puede contener letras, números y los símbolos _ - . @",
        )
    return v


class ProfileTypeResponse(BaseModel):
    id: str
    name: str
    user_count: int


class CreateProfileTypeRequest(BaseModel):
    name: str

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, v: str) -> str:
        return _validate_pt_name(v)


class UpdateProfileTypeRequest(BaseModel):
    name: str

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, v: str) -> str:
        return _validate_pt_name(v)


class UpdateUserRequest(BaseModel):
    password: str | None = None
    profile_type: str | None = None

    @field_validator("password", mode="before")
    @classmethod
    def validate_password(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if not v:
            return None
        if len(v) < 6:
            raise PydanticCustomError(
                "validation_error", "La contraseña debe tener al menos 6 caracteres"
            )
        if len(v) > 128:
            raise PydanticCustomError(
                "validation_error", "La contraseña no puede superar los 128 caracteres"
            )
        if not _PASSWORD_RE.match(v):
            raise PydanticCustomError(
                "validation_error",
                "La contraseña solo puede contener letras, números"
                " y los símbolos _ - . @ ! # $ % & * + = ?",
            )
        return v
