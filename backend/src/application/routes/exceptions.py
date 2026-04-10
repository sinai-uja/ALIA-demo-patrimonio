"""Typed application exceptions for the routes bounded context."""

from src.application.shared.exceptions import (
    ApplicationError,
    ResourceNotFoundError,
)


class RouteNotFoundError(ResourceNotFoundError):
    """Raised when a requested virtual route does not exist."""


class RouteGenerationError(ApplicationError):
    """Raised when a route cannot be generated for application reasons."""
