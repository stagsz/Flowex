"""Redis-based OAuth state storage for CSRF protection.

Uses Redis for distributed state storage in production,
with automatic fallback to in-memory storage if Redis is unavailable.

Security features:
- Cryptographically secure random state generation (32 bytes)
- 5-minute expiration to prevent replay attacks
- Single-use states (consumed after validation)
- Automatic cleanup of expired states
"""

import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from app.core.config import settings


class OAuthStateStorage:
    """Abstract base for OAuth state storage."""

    def store(
        self,
        state: str,
        user_id: UUID,
        org_id: UUID,
        provider: str,
    ) -> None:
        """Store OAuth state data."""
        raise NotImplementedError

    def validate_and_consume(self, state: str) -> dict[str, str] | None:
        """Validate state and consume it (single use).

        Returns:
            State data dict with user_id, org_id, provider if valid, None otherwise.
        """
        raise NotImplementedError


class RedisOAuthStateStorage(OAuthStateStorage):
    """Redis-based OAuth state storage for distributed deployments."""

    STATE_PREFIX = "oauth_state:"
    STATE_TTL_SECONDS = 300  # 5 minutes

    def __init__(self) -> None:
        import redis

        self._redis = redis.from_url(settings.REDIS_URL)  # type: ignore[no-untyped-call]

    def store(
        self,
        state: str,
        user_id: UUID,
        org_id: UUID,
        provider: str,
    ) -> None:
        """Store OAuth state in Redis with TTL."""
        import json

        key = f"{self.STATE_PREFIX}{state}"
        data = {
            "user_id": str(user_id),
            "org_id": str(org_id),
            "provider": provider,
            "created_at": datetime.now(UTC).isoformat(),
        }
        self._redis.setex(key, self.STATE_TTL_SECONDS, json.dumps(data))

    def validate_and_consume(self, state: str) -> dict[str, str] | None:
        """Validate and consume state from Redis.

        Uses GETDEL for atomic get-and-delete to prevent race conditions.
        """
        import json

        key = f"{self.STATE_PREFIX}{state}"

        # Atomic get and delete - prevents replay attacks
        raw_data: bytes | None = self._redis.getdel(key)
        if raw_data is None:
            return None

        try:
            data: dict[str, Any] = json.loads(raw_data)
        except (json.JSONDecodeError, TypeError):
            return None

        # Return only the fields needed by the callback
        return {
            "user_id": data["user_id"],
            "org_id": data["org_id"],
            "provider": data["provider"],
        }


class InMemoryOAuthStateStorage(OAuthStateStorage):
    """In-memory OAuth state storage for development/testing.

    WARNING: Not suitable for production with multiple workers.
    States will be lost on restart and not shared between workers.
    """

    STATE_TTL = timedelta(minutes=5)

    def __init__(self) -> None:
        self._states: dict[str, dict[str, Any]] = {}

    def store(
        self,
        state: str,
        user_id: UUID,
        org_id: UUID,
        provider: str,
    ) -> None:
        """Store OAuth state in memory."""
        self._cleanup_expired()
        self._states[state] = {
            "user_id": str(user_id),
            "org_id": str(org_id),
            "provider": provider,
            "created_at": datetime.now(UTC),
        }

    def validate_and_consume(self, state: str) -> dict[str, str] | None:
        """Validate and consume state from memory."""
        self._cleanup_expired()

        if state not in self._states:
            return None

        data = self._states.pop(state)

        # Check expiration (redundant with cleanup, but explicit)
        created_at = data["created_at"]
        if datetime.now(UTC) - created_at > self.STATE_TTL:
            return None

        return {
            "user_id": data["user_id"],
            "org_id": data["org_id"],
            "provider": data["provider"],
        }

    def _cleanup_expired(self) -> None:
        """Remove expired states from memory."""
        now = datetime.now(UTC)
        expired = [
            state
            for state, data in self._states.items()
            if now - data["created_at"] > self.STATE_TTL
        ]
        for state in expired:
            del self._states[state]


def _create_storage() -> OAuthStateStorage:
    """Create the appropriate OAuth state storage backend.

    Tries Redis first, falls back to in-memory if unavailable.
    """
    try:
        import redis

        r = redis.from_url(settings.REDIS_URL)  # type: ignore[no-untyped-call]
        r.ping()
        return RedisOAuthStateStorage()
    except Exception:
        # Redis not available, fall back to in-memory
        return InMemoryOAuthStateStorage()


# Singleton storage instance
_storage: OAuthStateStorage | None = None


def get_oauth_state_storage() -> OAuthStateStorage:
    """Get the OAuth state storage singleton."""
    global _storage
    if _storage is None:
        _storage = _create_storage()
    return _storage


def generate_oauth_state(user_id: UUID, org_id: UUID, provider: str) -> str:
    """Generate and store a new OAuth state token.

    Args:
        user_id: ID of the user initiating OAuth
        org_id: ID of the user's organization
        provider: Cloud provider name (e.g., 'microsoft', 'google')

    Returns:
        Cryptographically secure random state token
    """
    state = secrets.token_urlsafe(32)
    storage = get_oauth_state_storage()
    storage.store(state, user_id, org_id, provider)
    return state


def validate_oauth_state(state: str) -> dict[str, str] | None:
    """Validate and consume an OAuth state token.

    This is a single-use validation - the state is removed after validation.

    Args:
        state: The state token from the OAuth callback

    Returns:
        Dict with user_id, org_id, provider if valid, None otherwise
    """
    storage = get_oauth_state_storage()
    return storage.validate_and_consume(state)


def reset_oauth_state_storage() -> None:
    """Reset the OAuth state storage singleton.

    Useful for testing to force re-creation of storage backend.
    """
    global _storage
    _storage = None
