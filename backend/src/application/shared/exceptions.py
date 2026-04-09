"""Application-layer exception hierarchy.

These exceptions express use-case level outcomes independent of transport
(HTTP) and persistence concerns. The API layer translates them into HTTP
responses via the global exception handlers.
"""


class ApplicationError(Exception):
    """Base class for all application-level errors."""


class ResourceNotFoundError(ApplicationError):
    """Raised when a requested resource does not exist."""


class ConflictError(ApplicationError):
    """Raised when an operation conflicts with the current state."""


class UnauthorizedActionError(ApplicationError):
    """Raised when the actor is not allowed to perform the action."""


class ValidationError(ApplicationError):
    """Raised when input fails application-level validation."""
