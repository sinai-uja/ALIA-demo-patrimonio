"""Domain-specific application exceptions for the auth context.

These extend the shared application exception hierarchy so the global
FastAPI exception handlers translate them into the appropriate HTTP
responses automatically.
"""

from __future__ import annotations

from src.application.shared.exceptions import (
    ApplicationError,
    ConflictError,
    ResourceNotFoundError,
    UnauthorizedActionError,
)

# --- Authentication / token errors (mapped to 401 by the API layer) ---------


class InvalidCredentialsError(ApplicationError):
    """Raised when login credentials are invalid."""


class InvalidTokenError(ApplicationError):
    """Raised when a JWT/refresh token is invalid or expired."""


# --- Not-found errors (mapped to 404) ---------------------------------------


class UserNotFoundError(ResourceNotFoundError):
    """Raised when a user cannot be located."""


class ProfileTypeNotFoundError(ResourceNotFoundError):
    """Raised when a profile type cannot be located."""


# --- Conflict errors (mapped to 409) ----------------------------------------


class UserAlreadyExistsError(ConflictError):
    """Raised when attempting to create a user whose username is taken."""


class ProfileTypeAlreadyExistsError(ConflictError):
    """Raised when attempting to create/rename a profile type to an existing name."""


class ProfileTypeInUseError(ConflictError):
    """Raised when attempting to delete a profile type that has users assigned."""


# --- Authorization errors (mapped to 403) -----------------------------------


class RootAdminProtectedError(UnauthorizedActionError):
    """Raised when attempting to modify/delete the root admin user."""


class AdminOnlyActionError(UnauthorizedActionError):
    """Raised when a non-root-admin tries to perform a root-admin-only action."""


class ProfileTypeProtectedError(UnauthorizedActionError):
    """Raised when attempting to rename/delete a protected profile type (e.g. 'admin')."""
