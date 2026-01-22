"""Rate limiting configuration for FastAPI endpoints.

Uses slowapi with Redis backend for distributed rate limiting.
Falls back to in-memory storage if Redis is unavailable.
"""

from collections.abc import Callable

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings


def _get_redis_url() -> str | None:
    """Get Redis URL if available and rate limiting is enabled."""
    if not settings.RATE_LIMIT_ENABLED:
        return None

    # Try to connect to Redis to verify it's available
    try:
        import redis

        r = redis.from_url(settings.REDIS_URL)
        r.ping()
        return settings.REDIS_URL
    except Exception:
        # Redis not available, fall back to in-memory
        return None


def _get_key_func() -> Callable[[Request], str]:
    """Get the key function for rate limiting.

    Uses remote IP address as the key.
    """
    return get_remote_address


# Determine storage backend
_redis_url = _get_redis_url()

# Initialize limiter with appropriate backend
if _redis_url:
    # Use Redis for distributed rate limiting (production)
    limiter = Limiter(
        key_func=_get_key_func(),
        storage_uri=_redis_url,
        strategy="fixed-window",
        enabled=settings.RATE_LIMIT_ENABLED,
    )
else:
    # Use in-memory storage (development/testing)
    limiter = Limiter(
        key_func=_get_key_func(),
        strategy="fixed-window",
        enabled=settings.RATE_LIMIT_ENABLED,
    )


def get_limiter() -> Limiter:
    """Get the configured rate limiter instance."""
    return limiter


# Rate limit decorators for common use cases
def login_limit() -> str:
    """Get rate limit string for login endpoint."""
    return settings.RATE_LIMIT_LOGIN


def callback_limit() -> str:
    """Get rate limit string for OAuth callback endpoint."""
    return settings.RATE_LIMIT_CALLBACK


def refresh_limit() -> str:
    """Get rate limit string for token refresh endpoint."""
    return settings.RATE_LIMIT_REFRESH


def default_limit() -> str:
    """Get default rate limit string."""
    return settings.RATE_LIMIT_DEFAULT
