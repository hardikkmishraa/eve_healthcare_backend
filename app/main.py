from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.logging import setup_logging, get_logger
from app.core.middleware import RequestLoggingMiddleware, SecurityHeadersMiddleware
from app.core.cache import is_redis_available, limiter
from app.api.v1.router import api_router
from app.db.session import engine

# ─── Configure structured logging before anything else ────────────────────────
setup_logging()
logger = get_logger(__name__)


from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(application: FastAPI):
    logger.info(
        "Application starting up",
        extra={
            "app_name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
            "debug": settings.DEBUG,
        }
    )
    redis_ok = is_redis_available()
    logger.info("Redis connectivity check", extra={"redis_available": redis_ok})
    if not redis_ok:
        logger.warning("Redis is unavailable — caching and rate limiting will degrade gracefully")
    yield
    logger.info("Application shutting down gracefully")


def create_application() -> FastAPI:
    application = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        lifespan=lifespan,
        description="""
## EVE Healthcare — Diagnostic Test Booking API

A production-grade backend service for booking diagnostic tests at healthcare centres
with simulated payment processing, Redis caching, rate limiting, background job processing,
and idempotent webhook handling.

### Key Features
- 🔐 **JWT Authentication** — Secure signup/login with bcrypt password hashing
- 🏥 **Diagnostic Catalogue** — Browse centres and available tests with pricing (Redis-cached)
- 📅 **Booking System** — Create, view, and cancel diagnostic test appointments
- 💳 **Simulated Payments** — Mock payment processing with configurable outcomes
- 🔁 **Idempotent Webhooks** — Safe repeated delivery with event deduplication + row locking
- ⚡ **Redis Caching** — 10-minute cache on catalogue endpoints with auto-invalidation
- 🛡️ **Rate Limiting** — Redis-backed rate limits on sensitive endpoints
- 🔔 **Background Jobs** — Celery tasks for notifications and stale booking cleanup
- 📊 **Structured Logging** — JSON logs with X-Request-ID correlation

### Booking Status Flow
`PENDING → CONFIRMED` (payment success) | `PENDING → FAILED` (payment failure)
`PENDING/CONFIRMED → CANCELLED` (user cancellation)
        """,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # ── Rate Limiter ──────────────────────────────────────────────────────────
    application.state.limiter = limiter
    application.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # ── Middleware (outermost first, applied in reverse) ──────────────────────
    application.add_middleware(SecurityHeadersMiddleware)
    application.add_middleware(RequestLoggingMiddleware)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Restrict to known origins in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Response-Time-Ms"],
    )

    # ── API Routes ────────────────────────────────────────────────────────────
    application.include_router(api_router, prefix=settings.API_V1_PREFIX)

    return application


app = create_application()


# ─── Health & Readiness Probes ────────────────────────────────────────────────

@app.get(
    "/health",
    tags=["Observability"],
    summary="Liveness probe — is the service running?",
)
def health_check():
    """
    Kubernetes/Docker liveness probe.
    Returns 200 if the service process is alive (does NOT check dependencies).
    """
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "service": settings.APP_NAME,
        "environment": settings.ENVIRONMENT,
    }


@app.get(
    "/ready",
    tags=["Observability"],
    summary="Readiness probe — are all dependencies up?",
)
def readiness_check():
    """
    Kubernetes/Docker readiness probe.
    Checks that PostgreSQL and Redis are reachable before marking the pod ready.
    Returns 503 if any dependency is unavailable.
    """
    checks = {}

    # PostgreSQL check
    try:
        with engine.connect() as conn:
            conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception as exc:
        checks["postgres"] = f"error: {exc}"

    # Redis check
    checks["redis"] = "ok" if is_redis_available() else "unavailable"

    all_ok = all(v == "ok" for v in checks.values())
    return JSONResponse(
        content={"status": "ready" if all_ok else "degraded", "checks": checks},
        status_code=status.HTTP_200_OK if all_ok else status.HTTP_503_SERVICE_UNAVAILABLE,
    )


@app.get("/", include_in_schema=False)
def root():
    return {
        "message": f"Welcome to {settings.APP_NAME} v{settings.APP_VERSION}",
        "docs": "/docs",
        "health": "/health",
        "ready": "/ready",
    }
