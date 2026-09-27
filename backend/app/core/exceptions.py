"""
Warp Ladger — Custom Exception Hierarchy & FastAPI Exception Handlers

Uses RFC 7807 Problem Details format for all error responses.
"""
from typing import Any

import structlog
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from jose import JWTError
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

log = structlog.get_logger(__name__)


# ─── Exception Hierarchy ────────────────────────────────────
class WarpLadgerError(Exception):
    """Base exception for all Warp Ladger errors."""

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code: str = "internal_error"
    message: str = "An unexpected error occurred."

    def __init__(self, message: str | None = None, **extra: Any) -> None:
        self.message = message or self.__class__.message
        if "code" in extra and extra["code"]:
            self.error_code = str(extra["code"])
        self.extra = extra
        super().__init__(self.message)


class AuthenticationError(WarpLadgerError):
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "authentication_failed"
    message = "Authentication required."


class InvalidCredentialsError(AuthenticationError):
    error_code = "invalid_credentials"
    message = "Invalid email or password."


class TokenExpiredError(AuthenticationError):
    error_code = "token_expired"
    message = "Your session has expired. Please log in again."


class TokenInvalidError(AuthenticationError):
    error_code = "token_invalid"
    message = "Invalid authentication token."


class EmailNotVerifiedError(AuthenticationError):
    error_code = "email_not_verified"
    message = "Please verify your email address before logging in."


class PermissionDeniedError(WarpLadgerError):
    status_code = status.HTTP_403_FORBIDDEN
    error_code = "permission_denied"
    message = "You do not have permission to perform this action."


class NotFoundError(WarpLadgerError):
    status_code = status.HTTP_404_NOT_FOUND
    error_code = "not_found"
    message = "The requested resource was not found."


class ConflictError(WarpLadgerError):
    status_code = status.HTTP_409_CONFLICT
    error_code = "conflict"
    message = "A resource with this identifier already exists."


class ValidationFailedError(WarpLadgerError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    error_code = "validation_failed"
    message = "The request data is invalid."


class RateLimitExceededError(WarpLadgerError):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    error_code = "rate_limit_exceeded"
    message = "Too many requests. Please try again later."


class OrganisationMembershipError(PermissionDeniedError):
    error_code = "not_org_member"
    message = "You are not a member of this organisation."


class InvitationError(WarpLadgerError):
    status_code = status.HTTP_400_BAD_REQUEST
    error_code = "invitation_error"
    message = "This invitation is invalid or has expired."


class BadRequestError(WarpLadgerError):
    status_code = status.HTTP_400_BAD_REQUEST
    error_code = "bad_request"
    message = "The request was invalid or contains invalid parameters."


class StorageError(WarpLadgerError):
    error_code = "storage_error"
    message = "A file storage error occurred."


# ─── Error Response Builder ───────────────────────────────────
def problem_detail(
    *,
    status_code: int,
    error_code: str,
    message: str,
    detail: Any = None,
    request: Request | None = None,
) -> JSONResponse:
    """Build an RFC 7807 Problem Details JSON response."""
    body: dict[str, Any] = {
        "error": error_code,
        "message": message,
        "detail": detail if detail is not None else message,
        "status": status_code,
    }
    if request:
        body["path"] = str(request.url.path)
    return JSONResponse(status_code=status_code, content=body)


# ─── Exception Handlers ───────────────────────────────────────
def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(WarpLadgerError)
    async def warp_ladger_handler(request: Request, exc: WarpLadgerError) -> JSONResponse:
        log.warning(
            "app_error",
            error_code=exc.error_code,
            message=exc.message,
            path=str(request.url.path),
        )
        return problem_detail(
            status_code=exc.status_code,
            error_code=exc.error_code,
            message=exc.message,
            request=request,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        errors = []
        for err in exc.errors():
            clean_err = dict(err)
            if "ctx" in clean_err and isinstance(clean_err["ctx"], dict):
                clean_err["ctx"] = {k: str(v) for k, v in clean_err["ctx"].items()}
            errors.append(clean_err)
        return problem_detail(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="validation_failed",
            message="Request validation failed.",
            detail=errors,
            request=request,
        )

    @app.exception_handler(JWTError)
    async def jwt_handler(request: Request, exc: JWTError) -> JSONResponse:
        return problem_detail(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="token_invalid",
            message="Invalid authentication token.",
            request=request,
        )

    @app.exception_handler(IntegrityError)
    async def integrity_handler(request: Request, exc: IntegrityError) -> JSONResponse:
        log.warning("db_integrity_error", detail=str(exc.orig), path=str(request.url.path))
        return problem_detail(
            status_code=status.HTTP_409_CONFLICT,
            error_code="conflict",
            message="A resource with this identifier already exists.",
            request=request,
        )

    @app.exception_handler(Exception)
    async def generic_handler(request: Request, exc: Exception) -> JSONResponse:
        log.exception("unhandled_error", exc_info=exc, path=str(request.url.path))
        return problem_detail(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="internal_error",
            message="An unexpected error occurred. Please try again later.",
            request=request,
        )
