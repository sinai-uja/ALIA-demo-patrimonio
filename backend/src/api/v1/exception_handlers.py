"""Global FastAPI exception handlers.

Translates application- and infrastructure-layer exceptions into HTTP
responses. This keeps use cases and adapters free of HTTP concerns while
ensuring the client always receives a consistent error envelope.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.application.auth.exceptions import (
    InvalidCredentialsError,
    InvalidTokenError,
)
from src.application.shared.exceptions import (
    ApplicationError,
    ConflictError,
    ResourceNotFoundError,
    UnauthorizedActionError,
    ValidationError,
)
from src.infrastructure.shared.exceptions import (
    ExternalServiceUnavailableError,
    LLMResponseParseError,
)

logger = logging.getLogger("iaph.api.exception_handlers")


def _body(exc: Exception) -> dict:
    return {"detail": str(exc)}


def register_exception_handlers(app: FastAPI) -> None:
    """Register the global exception handlers on the given FastAPI app."""

    @app.exception_handler(ResourceNotFoundError)
    async def _handle_not_found(
        request: Request, exc: ResourceNotFoundError
    ) -> JSONResponse:
        logger.warning("Resource not found: %s", exc)
        return JSONResponse(status_code=404, content=_body(exc))

    @app.exception_handler(ConflictError)
    async def _handle_conflict(
        request: Request, exc: ConflictError
    ) -> JSONResponse:
        logger.warning("Conflict: %s", exc)
        return JSONResponse(status_code=409, content=_body(exc))

    @app.exception_handler(UnauthorizedActionError)
    async def _handle_unauthorized_action(
        request: Request, exc: UnauthorizedActionError
    ) -> JSONResponse:
        logger.warning("Unauthorized action: %s", exc)
        return JSONResponse(status_code=403, content=_body(exc))

    @app.exception_handler(ValidationError)
    async def _handle_validation(
        request: Request, exc: ValidationError
    ) -> JSONResponse:
        logger.warning("Validation error: %s", exc)
        return JSONResponse(status_code=422, content=_body(exc))

    @app.exception_handler(ExternalServiceUnavailableError)
    async def _handle_external_unavailable(
        request: Request, exc: ExternalServiceUnavailableError
    ) -> JSONResponse:
        logger.error("External service unavailable: %s", exc)
        return JSONResponse(status_code=502, content=_body(exc))

    @app.exception_handler(LLMResponseParseError)
    async def _handle_llm_parse(
        request: Request, exc: LLMResponseParseError
    ) -> JSONResponse:
        logger.error("LLM response parse error: %s", exc)
        return JSONResponse(status_code=502, content=_body(exc))

    @app.exception_handler(InvalidCredentialsError)
    async def _handle_invalid_credentials(
        request: Request, exc: InvalidCredentialsError
    ) -> JSONResponse:
        logger.warning("Invalid credentials: %s", exc)
        return JSONResponse(
            status_code=401,
            content=_body(exc),
            headers={"WWW-Authenticate": "Bearer"},
        )

    @app.exception_handler(InvalidTokenError)
    async def _handle_invalid_token(
        request: Request, exc: InvalidTokenError
    ) -> JSONResponse:
        logger.warning("Invalid token: %s", exc)
        return JSONResponse(
            status_code=401,
            content=_body(exc),
            headers={"WWW-Authenticate": "Bearer"},
        )

    @app.exception_handler(ApplicationError)
    async def _handle_application_error(
        request: Request, exc: ApplicationError
    ) -> JSONResponse:
        logger.warning("Application error: %s", exc)
        return JSONResponse(status_code=400, content=_body(exc))
