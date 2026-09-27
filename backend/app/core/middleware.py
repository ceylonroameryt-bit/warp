"""
Warp Ladger — FastAPI Middleware Stack
Request IDs, security headers, timing, and rate limiting.
"""
import time
import uuid
from typing import Callable

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Match
from starlette.types import ASGIApp

log = structlog.get_logger(__name__)


# ─── Request ID Middleware ────────────────────────────────────
class RequestIDMiddleware(BaseHTTPMiddleware):
    """Injects a unique X-Request-ID header on every request/response."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


# ─── Timing Middleware ────────────────────────────────────────
class TimingMiddleware(BaseHTTPMiddleware):
    """Adds X-Process-Time header and logs slow requests."""

    SLOW_REQUEST_THRESHOLD_MS = 1000

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        response.headers["X-Process-Time"] = f"{duration_ms}ms"

        if duration_ms > self.SLOW_REQUEST_THRESHOLD_MS:
            log.warning(
                "slow_request",
                method=request.method,
                path=request.url.path,
                duration_ms=duration_ms,
            )
        return response


# ─── Security Headers Middleware ──────────────────────────────
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds security headers to every response."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        if "location" in response.headers:
            loc = response.headers["location"]
            for prefix in ("https://127.0.0.1:8001", "http://127.0.0.1:8001", "https://localhost:8001", "http://localhost:8001"):
                if loc.startswith(prefix):
                    response.headers["location"] = loc[len(prefix):]
                    break
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=()"
        )
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )
        # HSTS — only on HTTPS
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )
        return response


# ─── Trailing Slash Normalization Middleware ─────────────────
class TrailingSlashMiddleware(BaseHTTPMiddleware):
    """
    Prevents 307 redirects for missing trailing slashes by matching routes
    internally and rewriting scope path so proxies and tunnels don't loop.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        if not path.endswith("/") and "." not in path.split("/")[-1]:
            test_scope = dict(request.scope)
            test_scope["path"] = path + "/"
            for route in request.app.routes:
                match, _ = route.matches(test_scope)
                if match == Match.FULL:
                    request.scope["path"] = path + "/"
                    break
        return await call_next(request)

