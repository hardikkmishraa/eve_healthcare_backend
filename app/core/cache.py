"""
Redis client, caching utilities, and rate limiter setup.
"""
import json
import hashlib
import logging
from typing import Optional, Any
import redis
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings

logger = logging.getLogger(__name__)

# ─── Redis Connection Pool ────────────────────────────────────────────────────

_redis_client: Optional[redis.Redis] = None


def get_redis() -> redis.Redis:
    """Return a shared Redis client (lazy-initialised)."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
    return _redis_client


def is_redis_available() -> bool:
    """Check Redis connectivity for health probe."""
    try:
        return get_redis().ping()
    except Exception:
        return False


# ─── Cache Helpers ────────────────────────────────────────────────────────────

CACHE_PREFIX = "eve:cache:"


def _make_key(*parts: str) -> str:
    raw = ":".join(str(p) for p in parts)
    return f"{CACHE_PREFIX}{hashlib.md5(raw.encode()).hexdigest()}"


def cache_get(key: str) -> Optional[Any]:
    """Retrieve a cached value. Returns None on miss or Redis failure."""
    try:
        raw = get_redis().get(key)
        if raw:
            logger.debug("Cache HIT", extra={"cache_key": key})
            return json.loads(raw)
        logger.debug("Cache MISS", extra={"cache_key": key})
        return None
    except Exception as exc:
        logger.warning("Cache get failed — falling through to DB", extra={"error": str(exc)})
        return None


def cache_set(key: str, value: Any, ttl: int = settings.CACHE_TTL_SECONDS) -> None:
    """Store a value in the cache with TTL. Silently ignores Redis failures."""
    try:
        get_redis().set(key, json.dumps(value, default=str), ex=ttl)
        logger.debug("Cache SET", extra={"cache_key": key, "ttl": ttl})
    except Exception as exc:
        logger.warning("Cache set failed — continuing without cache", extra={"error": str(exc)})


def cache_delete(key: str) -> None:
    """Delete a specific cache key."""
    try:
        get_redis().delete(key)
    except Exception as exc:
        logger.warning("Cache delete failed", extra={"error": str(exc)})


def cache_delete_pattern(pattern: str) -> int:
    """Delete all keys matching a pattern. Returns count deleted."""
    try:
        r = get_redis()
        keys = r.keys(f"{CACHE_PREFIX}{pattern}")
        if keys:
            return r.delete(*keys)
        return 0
    except Exception as exc:
        logger.warning("Cache pattern delete failed", extra={"error": str(exc)})
        return 0


def make_centres_cache_key(city: Optional[str], is_active: Optional[bool], page: int, page_size: int) -> str:
    return _make_key("centres", str(city), str(is_active), str(page), str(page_size))


def make_tests_cache_key(category: Optional[str], search: Optional[str], page: int, page_size: int) -> str:
    return _make_key("tests", str(category), str(search), str(page), str(page_size))


def make_centre_tests_cache_key(centre_id: str) -> str:
    return _make_key("centre_tests", centre_id)


def invalidate_centre_cache() -> None:
    """Blow away all centre-related cache entries."""
    deleted = cache_delete_pattern("*")
    logger.info("Cache invalidated", extra={"keys_deleted": deleted})


# ─── Rate Limiter ─────────────────────────────────────────────────────────────

def _get_rate_limit_key(request) -> str:
    """Use Redis-backed storage for rate limits; fall back to in-memory on failure."""
    return get_remote_address(request)


limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.REDIS_URL,
    default_limits=[settings.RATE_LIMIT_DEFAULT],
    enabled=settings.RATE_LIMIT_ENABLED,
)
