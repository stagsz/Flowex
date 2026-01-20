"""Tests for Redis-based OAuth state storage."""

import time
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.core.oauth_state import (
    InMemoryOAuthStateStorage,
    RedisOAuthStateStorage,
    generate_oauth_state,
    get_oauth_state_storage,
    reset_oauth_state_storage,
    validate_oauth_state,
)


class TestInMemoryOAuthStateStorage:
    """Tests for in-memory OAuth state storage."""

    def test_store_and_validate(self):
        """Test storing and validating state."""
        storage = InMemoryOAuthStateStorage()
        user_id = uuid4()
        org_id = uuid4()

        storage.store("test_state", user_id, org_id, "microsoft")

        result = storage.validate_and_consume("test_state")

        assert result is not None
        assert result["user_id"] == str(user_id)
        assert result["org_id"] == str(org_id)
        assert result["provider"] == "microsoft"

    def test_state_consumed_after_validation(self):
        """Test that state is consumed (single-use) after validation."""
        storage = InMemoryOAuthStateStorage()
        user_id = uuid4()
        org_id = uuid4()

        storage.store("test_state", user_id, org_id, "google")

        # First validation should succeed
        result1 = storage.validate_and_consume("test_state")
        assert result1 is not None

        # Second validation should fail (state consumed)
        result2 = storage.validate_and_consume("test_state")
        assert result2 is None

    def test_invalid_state_returns_none(self):
        """Test that invalid state returns None."""
        storage = InMemoryOAuthStateStorage()

        result = storage.validate_and_consume("nonexistent_state")
        assert result is None

    def test_expired_state_returns_none(self):
        """Test that expired state returns None."""
        storage = InMemoryOAuthStateStorage()
        user_id = uuid4()
        org_id = uuid4()

        # Store state
        storage.store("test_state", user_id, org_id, "microsoft")

        # Manually set created_at to 6 minutes ago (past 5-minute TTL)
        storage._states["test_state"]["created_at"] = datetime.now(UTC) - timedelta(
            minutes=6
        )

        result = storage.validate_and_consume("test_state")
        assert result is None

    def test_cleanup_expired_states(self):
        """Test automatic cleanup of expired states."""
        storage = InMemoryOAuthStateStorage()

        # Create multiple states with different ages
        for i in range(5):
            storage.store(f"state_{i}", uuid4(), uuid4(), "microsoft")

        # Make some states expired
        storage._states["state_0"]["created_at"] = datetime.now(UTC) - timedelta(
            minutes=10
        )
        storage._states["state_1"]["created_at"] = datetime.now(UTC) - timedelta(
            minutes=10
        )

        # Cleanup happens on store
        storage.store("new_state", uuid4(), uuid4(), "google")

        # Expired states should be removed
        assert "state_0" not in storage._states
        assert "state_1" not in storage._states
        # Fresh states should remain
        assert "state_2" in storage._states
        assert "state_3" in storage._states
        assert "state_4" in storage._states
        assert "new_state" in storage._states


class TestRedisOAuthStateStorage:
    """Tests for Redis-based OAuth state storage."""

    def test_store_and_validate_with_mock(self):
        """Test storing and validating state with mocked Redis."""
        import json

        mock_redis = MagicMock()
        user_id = uuid4()
        org_id = uuid4()

        with patch("app.core.oauth_state.settings") as mock_settings, patch(
            "redis.from_url", return_value=mock_redis
        ):
            mock_settings.REDIS_URL = "redis://localhost:6379"

            storage = RedisOAuthStateStorage()

            # Test store
            storage.store("test_state", user_id, org_id, "microsoft")

            # Verify setex was called with correct TTL
            mock_redis.setex.assert_called_once()
            call_args = mock_redis.setex.call_args
            assert call_args[0][0] == "oauth_state:test_state"
            assert call_args[0][1] == 300  # 5 minutes TTL
            stored_data = json.loads(call_args[0][2])
            assert stored_data["user_id"] == str(user_id)
            assert stored_data["org_id"] == str(org_id)
            assert stored_data["provider"] == "microsoft"

    def test_validate_and_consume_with_mock(self):
        """Test validate and consume with mocked Redis."""
        import json

        mock_redis = MagicMock()
        user_id = uuid4()
        org_id = uuid4()

        # Simulate stored data
        stored_data = json.dumps(
            {
                "user_id": str(user_id),
                "org_id": str(org_id),
                "provider": "google",
                "created_at": datetime.now(UTC).isoformat(),
            }
        ).encode()

        mock_redis.getdel.return_value = stored_data

        with patch("app.core.oauth_state.settings") as mock_settings, patch(
            "redis.from_url", return_value=mock_redis
        ):
            mock_settings.REDIS_URL = "redis://localhost:6379"

            storage = RedisOAuthStateStorage()
            result = storage.validate_and_consume("test_state")

            # Verify getdel was called (atomic get and delete)
            mock_redis.getdel.assert_called_once_with("oauth_state:test_state")

            assert result is not None
            assert result["user_id"] == str(user_id)
            assert result["org_id"] == str(org_id)
            assert result["provider"] == "google"

    def test_validate_nonexistent_state_with_mock(self):
        """Test validating nonexistent state returns None."""
        mock_redis = MagicMock()
        mock_redis.getdel.return_value = None

        with patch("app.core.oauth_state.settings") as mock_settings, patch(
            "redis.from_url", return_value=mock_redis
        ):
            mock_settings.REDIS_URL = "redis://localhost:6379"

            storage = RedisOAuthStateStorage()
            result = storage.validate_and_consume("nonexistent")

            assert result is None

    def test_validate_invalid_json_returns_none(self):
        """Test validating state with invalid JSON returns None."""
        mock_redis = MagicMock()
        mock_redis.getdel.return_value = b"not valid json"

        with patch("app.core.oauth_state.settings") as mock_settings, patch(
            "redis.from_url", return_value=mock_redis
        ):
            mock_settings.REDIS_URL = "redis://localhost:6379"

            storage = RedisOAuthStateStorage()
            result = storage.validate_and_consume("bad_state")

            assert result is None


class TestOAuthStateFunctions:
    """Tests for OAuth state module functions."""

    def setup_method(self):
        """Reset storage before each test."""
        reset_oauth_state_storage()

    def test_generate_oauth_state(self):
        """Test generating OAuth state."""
        user_id = uuid4()
        org_id = uuid4()

        with patch(
            "app.core.oauth_state.get_oauth_state_storage"
        ) as mock_get_storage:
            mock_storage = MagicMock()
            mock_get_storage.return_value = mock_storage

            state = generate_oauth_state(user_id, org_id, "microsoft")

            # State should be cryptographically random
            assert len(state) > 20
            # Storage should be called
            mock_storage.store.assert_called_once_with(
                state, user_id, org_id, "microsoft"
            )

    def test_validate_oauth_state(self):
        """Test validating OAuth state."""
        expected_data = {"user_id": "123", "org_id": "456", "provider": "google"}

        with patch(
            "app.core.oauth_state.get_oauth_state_storage"
        ) as mock_get_storage:
            mock_storage = MagicMock()
            mock_storage.validate_and_consume.return_value = expected_data
            mock_get_storage.return_value = mock_storage

            result = validate_oauth_state("test_state")

            assert result == expected_data
            mock_storage.validate_and_consume.assert_called_once_with("test_state")

    def test_validate_invalid_state(self):
        """Test validating invalid OAuth state."""
        with patch(
            "app.core.oauth_state.get_oauth_state_storage"
        ) as mock_get_storage:
            mock_storage = MagicMock()
            mock_storage.validate_and_consume.return_value = None
            mock_get_storage.return_value = mock_storage

            result = validate_oauth_state("invalid_state")

            assert result is None

    def test_get_storage_creates_redis_when_available(self):
        """Test that Redis storage is created when Redis is available."""
        mock_redis = MagicMock()

        with patch("redis.from_url", return_value=mock_redis):
            mock_redis.ping.return_value = True

            reset_oauth_state_storage()
            storage = get_oauth_state_storage()

            assert isinstance(storage, RedisOAuthStateStorage)

    def test_get_storage_falls_back_to_memory(self):
        """Test that in-memory storage is used when Redis is unavailable."""
        with patch("redis.from_url") as mock_from_url:
            mock_from_url.side_effect = Exception("Redis connection failed")

            reset_oauth_state_storage()
            storage = get_oauth_state_storage()

            assert isinstance(storage, InMemoryOAuthStateStorage)

    def test_storage_singleton(self):
        """Test that storage is a singleton."""
        with patch("redis.from_url") as mock_from_url:
            mock_from_url.side_effect = Exception("Redis unavailable")

            reset_oauth_state_storage()
            storage1 = get_oauth_state_storage()
            storage2 = get_oauth_state_storage()

            assert storage1 is storage2


class TestIntegration:
    """Integration tests for the full OAuth state flow."""

    def setup_method(self):
        """Reset storage before each test."""
        reset_oauth_state_storage()

    def test_full_oauth_flow_in_memory(self):
        """Test full OAuth flow with in-memory storage."""
        with patch("redis.from_url") as mock_from_url:
            # Force in-memory storage
            mock_from_url.side_effect = Exception("Redis unavailable")

            reset_oauth_state_storage()

            user_id = uuid4()
            org_id = uuid4()

            # Generate state
            state = generate_oauth_state(user_id, org_id, "microsoft")
            assert state is not None

            # Validate state (simulates OAuth callback)
            result = validate_oauth_state(state)
            assert result is not None
            assert result["user_id"] == str(user_id)
            assert result["org_id"] == str(org_id)
            assert result["provider"] == "microsoft"

            # State should be consumed (single-use)
            result2 = validate_oauth_state(state)
            assert result2 is None

    def test_multiple_concurrent_states(self):
        """Test multiple OAuth states can coexist."""
        with patch("redis.from_url") as mock_from_url:
            mock_from_url.side_effect = Exception("Redis unavailable")

            reset_oauth_state_storage()

            # Generate multiple states
            states = []
            for i in range(5):
                user_id = uuid4()
                org_id = uuid4()
                state = generate_oauth_state(user_id, org_id, f"provider_{i}")
                states.append((state, str(user_id), str(org_id), f"provider_{i}"))

            # Validate each state
            for state, user_id, org_id, provider in states:
                result = validate_oauth_state(state)
                assert result is not None
                assert result["user_id"] == user_id
                assert result["org_id"] == org_id
                assert result["provider"] == provider

            # All states should now be consumed
            for state, _, _, _ in states:
                result = validate_oauth_state(state)
                assert result is None
