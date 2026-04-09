"""Chat context application-level exceptions."""

from src.application.shared.exceptions import ResourceNotFoundError


class SessionNotFoundError(ResourceNotFoundError):
    """Raised when a chat session does not exist or is not accessible to the actor."""
