"""Domain exceptions and a standardized error envelope.

Every error the API returns has the same JSON shape::

    {"error": {"code": "...", "message": "...", "details": ...}}

A predictable error contract is one of the clearest signals of a
professionally built API, and it makes client-side handling trivial.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppError(Exception):
    """Base class for all expected, business-level errors.

    Carrying an HTTP status, a stable machine-readable ``code`` and an
    optional ``details`` payload lets us map any domain failure onto the
    error envelope in one place.
    """

    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "APP_ERROR"

    def __init__(
        self,
        message: str,
        *,
        details: Any | None = None,
        status_code: int | None = None,
        code: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.details = details
        if status_code is not None:
            self.status_code = status_code
        if code is not None:
            self.code = code


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "NOT_FOUND"


class ConflictError(AppError):
    status_code = status.HTTP_409_CONFLICT
    code = "CONFLICT"


class AuthenticationError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "AUTHENTICATION_FAILED"


class AuthorizationError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "FORBIDDEN"


class ValidationAppError(AppError):
    status_code = 422  # avoid deprecated Starlette constant name
    code = "VALIDATION_ERROR"


class UpstreamError(AppError):
    """A dependency (e.g. an external data source) failed or was unreachable."""

    status_code = status.HTTP_502_BAD_GATEWAY
    code = "UPSTREAM_ERROR"


class NoDataError(UpstreamError):
    """An upstream request succeeded but returned no usable data points."""

    code = "NO_DATA_RETURNED"


def _envelope(code: str, message: str, details: Any | None = None) -> dict[str, Any]:
    return {"error": {"code": code, "message": message, "details": details}}


def register_exception_handlers(app: FastAPI) -> None:
    """Attach handlers that render every error in the standard envelope."""

    @app.exception_handler(AppError)
    async def _handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_envelope(exc.code, exc.message, exc.details),
        )

    @app.exception_handler(RequestValidationError)
    async def _handle_validation(
        _: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=_envelope(
                "VALIDATION_ERROR",
                "Request validation failed.",
                exc.errors(),
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _handle_http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        # Reuse Starlette's status phrase as a stable-ish code.
        code = {
            401: "AUTHENTICATION_FAILED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
        }.get(exc.status_code, "HTTP_ERROR")
        return JSONResponse(
            status_code=exc.status_code,
            content=_envelope(code, str(exc.detail)),
        )
