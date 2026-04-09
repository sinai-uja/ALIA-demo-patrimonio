"""Shared async httpx helpers with typed error translation.

All outbound HTTP calls from infrastructure adapters (LLM, embedding,
reranker, etc.) should go through these helpers so that low-level
``httpx.HTTPError`` / ``httpx.HTTPStatusError`` exceptions are consistently
translated into the project's typed infrastructure exceptions
(``ExternalServiceUnavailableError`` and its specializations).

Non-httpx exceptions (parse errors, cancellations, programming errors) are
intentionally NOT swallowed here — they propagate to the caller unchanged.
"""
from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

import httpx

from src.application.shared.exceptions import ExternalServiceUnavailableError

_logger = logging.getLogger("iaph.infra.httpx")


def _translate_status_error(
    exc: httpx.HTTPStatusError,
    *,
    service_label: str,
    url: str,
    error_class: type[ExternalServiceUnavailableError],
) -> ExternalServiceUnavailableError:
    status = exc.response.status_code
    try:
        body_preview = exc.response.text[:500]
    except Exception:  # noqa: BLE001 - defensive, body may be unreadable
        body_preview = "<unreadable body>"
    _logger.warning(
        "%s HTTP %s on %s — %s", service_label, status, url, body_preview,
    )
    return error_class(
        f"{service_label} returned HTTP {status}",
    )


def _translate_transport_error(
    exc: httpx.HTTPError,
    *,
    service_label: str,
    url: str,
    error_class: type[ExternalServiceUnavailableError],
) -> ExternalServiceUnavailableError:
    _logger.warning("%s HTTP error on %s — %s", service_label, url, exc)
    return error_class(f"{service_label} unreachable: {exc}")


async def post_json(
    url: str,
    payload: Any,
    *,
    service_label: str,
    timeout: float = 60.0,
    headers: Mapping[str, str] | None = None,
    error_class: type[ExternalServiceUnavailableError] = ExternalServiceUnavailableError,
) -> Any:
    """POST ``payload`` as JSON to ``url`` and return the parsed JSON body.

    Any ``httpx.HTTPStatusError`` or ``httpx.HTTPError`` is re-raised as
    ``error_class`` (default: ``ExternalServiceUnavailableError``) with the
    original exception chained via ``raise ... from exc``.
    """
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                url,
                json=payload,
                headers=dict(headers) if headers else None,
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as exc:
        raise _translate_status_error(
            exc,
            service_label=service_label,
            url=url,
            error_class=error_class,
        ) from exc
    except httpx.HTTPError as exc:
        raise _translate_transport_error(
            exc,
            service_label=service_label,
            url=url,
            error_class=error_class,
        ) from exc


async def get_json(
    url: str,
    *,
    service_label: str,
    timeout: float = 60.0,
    headers: Mapping[str, str] | None = None,
    params: Mapping[str, Any] | None = None,
    error_class: type[ExternalServiceUnavailableError] = ExternalServiceUnavailableError,
) -> Any:
    """GET ``url`` and return the parsed JSON body with typed error translation."""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(
                url,
                headers=dict(headers) if headers else None,
                params=dict(params) if params else None,
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as exc:
        raise _translate_status_error(
            exc,
            service_label=service_label,
            url=url,
            error_class=error_class,
        ) from exc
    except httpx.HTTPError as exc:
        raise _translate_transport_error(
            exc,
            service_label=service_label,
            url=url,
            error_class=error_class,
        ) from exc
