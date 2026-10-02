"""
FastAPI middleware collection:
1. RequestLoggingMiddleware  — structured request/response logging with latency + X-Request-ID
2. SecurityHeadersMiddleware — injects security headers on every response
"""
import time
import uuid
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

# Thread-local storage for correlation ID (used by logging filter)
import contextvars
_request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id", default="N/A"
)


def get_current_request_id() -> str:
    return _request_id_var.get()


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    For every HTTP request:
    - Generates or extracts X-Request-ID correlation ID
    - Logs incoming request (method, path, client IP)
    - Logs outgoing response (status code, latency in ms)
    - Injects X-Request-ID header into the response
    """

    SKIP_PATHS = {"/health", "/ready", "/", "/openapi.json", "/favicon.ico"}

    async def dispatch(self, request: Request, call_next) -> Response:
        # Resolve correlation ID
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        _request_id_var.set(request_id)

        path = request.url.path
        method = request.method
        client_ip = request.client.host if request.client else "unknown"

        start_time = time.perf_counter()

        if path not in self.SKIP_PATHS:
            logger.info(
                "Incoming request",
                extra={
                    "request_id": request_id,
                    "method": method,
                    "path": path,
                    "client_ip": client_ip,
                    "query_params": str(request.query_params) or None,
                },
            )

        response: Response = await call_next(request)

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        if path not in self.SKIP_PATHS:
            level = logging.WARNING if response.status_code >= 400 else logging.INFO
            logger.log(
                level,
                "Request completed",
                extra={
                    "request_id": request_id,
                    "method": method,
                    "path": path,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                },
            )

        # Inject correlation ID and timing into response headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time-Ms"] = str(duration_ms)
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Injects OWASP-recommended security headers on every response."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=()"
        return response
