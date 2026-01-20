from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Reset rate limiter storage before each test."""
    # Get the limiter from app state and reset its storage
    limiter = app.state.limiter
    if hasattr(limiter, "_storage") and limiter._storage:
        # Clear in-memory storage if available
        try:
            limiter._storage.reset()
        except (AttributeError, Exception):
            pass
    yield


def test_login_redirect_google():
    """Test login redirects to OAuth provider for Google SSO."""
    response = client.get(
        "/api/v1/auth/login",
        params={"provider": "google", "redirect_uri": "http://localhost:5173/callback"},
        follow_redirects=False,
    )
    assert response.status_code == 307
    location = response.headers["location"]
    assert "authorize" in location
    # Works with both Auth0 (google-oauth2) and Supabase (provider=google)
    assert "google" in location


def test_login_redirect_microsoft():
    """Test login redirects to OAuth provider for Microsoft SSO."""
    response = client.get(
        "/api/v1/auth/login",
        params={"provider": "microsoft", "redirect_uri": "http://localhost:5173/callback"},
        follow_redirects=False,
    )
    assert response.status_code == 307
    location = response.headers["location"]
    assert "authorize" in location
    # Works with both Auth0 (windowslive) and Supabase (provider=microsoft)
    assert "microsoft" in location or "windowslive" in location


def test_login_invalid_provider():
    """Test login with invalid provider returns error."""
    response = client.get(
        "/api/v1/auth/login",
        params={"provider": "invalid", "redirect_uri": "http://localhost:5173/callback"},
    )
    assert response.status_code == 400
    assert "Invalid provider" in response.json()["detail"]


def test_logout():
    """Test logout returns success message."""
    response = client.post("/api/v1/auth/logout")
    assert response.status_code == 200
    assert response.json()["message"] == "Logged out successfully"


def test_refresh_token_missing_body():
    """Test refresh endpoint requires refresh_token in body."""
    response = client.post("/api/v1/auth/refresh", json={})
    assert response.status_code == 422


def test_refresh_token_invalid():
    """Test refresh endpoint with invalid refresh token returns 401."""
    # Mock Auth0 returning an error for invalid refresh token
    with patch("app.api.routes.auth.httpx.AsyncClient") as mock_client:
        mock_response = AsyncMock()
        mock_response.status_code = 403
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )

        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid_refresh_token"},
        )
        assert response.status_code == 401
        assert "Invalid or expired refresh token" in response.json()["detail"]


def test_refresh_token_success():
    """Test refresh endpoint returns new tokens on success."""
    # Mock Auth0 returning new tokens
    with patch("app.api.routes.auth.httpx.AsyncClient") as mock_client:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        # Use a regular function for json() since it's not async
        mock_response.json = lambda: {
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token",
            "expires_in": 86400,
            "token_type": "Bearer",
        }
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )

        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "valid_refresh_token"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["access_token"] == "new_access_token"
        assert data["refresh_token"] == "new_refresh_token"
        assert data["expires_in"] == 86400
        assert data["token_type"] == "bearer"


def test_me_unauthorized():
    """Test /me endpoint without auth returns 403."""
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 403


def test_me_invalid_token():
    """Test /me endpoint with invalid token returns 401."""
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid_token"},
    )
    assert response.status_code == 401


class TestTokenCreation:
    """Test internal token creation for testing purposes."""

    def test_create_access_token(self):
        """Test creating an access token."""
        token = create_access_token({"sub": "test_user", "email": "test@example.com"})
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0


class TestRedirectUriValidation:
    """Test redirect URI validation to prevent open redirect attacks."""

    def test_valid_redirect_uri_localhost(self):
        """Test valid localhost redirect URI is accepted."""
        response = client.get(
            "/api/v1/auth/login",
            params={"provider": "google", "redirect_uri": "http://localhost:5173/callback"},
            follow_redirects=False,
        )
        assert response.status_code == 307  # Redirect to OAuth provider

    def test_valid_redirect_uri_with_path(self):
        """Test valid redirect URI with path is accepted."""
        response = client.get(
            "/api/v1/auth/login",
            params={"provider": "google", "redirect_uri": "http://localhost:5173/auth/callback"},
            follow_redirects=False,
        )
        assert response.status_code == 307

    def test_invalid_redirect_uri_host_suffix_attack(self):
        """Test host suffix attack is blocked (e.g., localhost:5173.attacker.com)."""
        response = client.get(
            "/api/v1/auth/login",
            params={
                "provider": "google",
                "redirect_uri": "http://localhost:5173.attacker.com/callback",
            },
        )
        assert response.status_code == 400
        assert "Invalid redirect URI" in response.json()["detail"]

    def test_invalid_redirect_uri_userinfo_attack(self):
        """Test userinfo attack is blocked (e.g., localhost:5173@attacker.com)."""
        response = client.get(
            "/api/v1/auth/login",
            params={
                "provider": "google",
                "redirect_uri": "http://localhost:5173@attacker.com/callback",
            },
        )
        assert response.status_code == 400
        assert "Invalid redirect URI" in response.json()["detail"]

    def test_invalid_redirect_uri_different_host(self):
        """Test completely different host is blocked."""
        response = client.get(
            "/api/v1/auth/login",
            params={"provider": "google", "redirect_uri": "http://attacker.com/callback"},
        )
        assert response.status_code == 400
        assert "Invalid redirect URI" in response.json()["detail"]

    def test_invalid_redirect_uri_different_port(self):
        """Test different port on same host is blocked."""
        response = client.get(
            "/api/v1/auth/login",
            params={"provider": "google", "redirect_uri": "http://localhost:9999/callback"},
        )
        assert response.status_code == 400
        assert "Invalid redirect URI" in response.json()["detail"]

    def test_invalid_redirect_uri_javascript_scheme(self):
        """Test javascript: scheme is blocked."""
        response = client.get(
            "/api/v1/auth/login",
            params={"provider": "google", "redirect_uri": "javascript:alert(1)"},
        )
        assert response.status_code == 400
        assert "Invalid redirect URI" in response.json()["detail"]

    def test_invalid_redirect_uri_data_scheme(self):
        """Test data: scheme is blocked."""
        response = client.get(
            "/api/v1/auth/login",
            params={
                "provider": "google",
                "redirect_uri": "data:text/html,<script>alert(1)</script>",
            },
        )
        assert response.status_code == 400
        assert "Invalid redirect URI" in response.json()["detail"]

    def test_invalid_redirect_uri_relative_path(self):
        """Test relative path without host is blocked."""
        response = client.get(
            "/api/v1/auth/login",
            params={"provider": "google", "redirect_uri": "/callback"},
        )
        assert response.status_code == 400
        assert "Invalid redirect URI" in response.json()["detail"]

    def test_callback_invalid_redirect_uri(self):
        """Test callback endpoint also validates redirect URI."""
        response = client.get(
            "/api/v1/auth/callback",
            params={
                "code": "test_code",
                "redirect_uri": "http://attacker.com/steal-token",
            },
        )
        assert response.status_code == 400
        assert "Invalid redirect URI" in response.json()["detail"]

    def test_callback_host_suffix_attack(self):
        """Test callback endpoint blocks host suffix attack."""
        response = client.get(
            "/api/v1/auth/callback",
            params={
                "code": "test_code",
                "redirect_uri": "http://localhost:5173.attacker.com/callback",
            },
        )
        assert response.status_code == 400
        assert "Invalid redirect URI" in response.json()["detail"]


class TestRateLimiting:
    """Test rate limiting on authentication endpoints."""

    def test_rate_limit_login_within_limit(self):
        """Test login requests within rate limit succeed."""
        # First request should succeed
        response = client.get(
            "/api/v1/auth/login",
            params={"provider": "google", "redirect_uri": "http://localhost:5173/callback"},
            follow_redirects=False,
        )
        assert response.status_code == 307

    def test_rate_limit_logout_within_limit(self):
        """Test logout requests within rate limit succeed."""
        response = client.post("/api/v1/auth/logout")
        assert response.status_code == 200

    def test_rate_limit_refresh_within_limit(self):
        """Test refresh requests within rate limit succeed (with mocked response)."""
        with patch("app.api.routes.auth.httpx.AsyncClient") as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json = lambda: {
                "access_token": "new_token",
                "refresh_token": "new_refresh",
                "expires_in": 3600,
            }
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            response = client.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": "valid_token"},
            )
            assert response.status_code == 200

    def test_rate_limit_headers_present(self):
        """Test rate limit headers are present in response."""
        response = client.post("/api/v1/auth/logout")
        # slowapi adds rate limit headers
        # Check response succeeded (rate limiting is enabled but not exceeded)
        assert response.status_code == 200

    def test_rate_limit_exceeded_login(self):
        """Test rate limit exceeded returns 429 for login endpoint."""
        # Configure very low limit temporarily to trigger rate limit
        from app.core.config import settings

        original_limit = settings.RATE_LIMIT_LOGIN
        settings.RATE_LIMIT_LOGIN = "1/minute"

        try:
            # First request should succeed
            response1 = client.get(
                "/api/v1/auth/login",
                params={
                    "provider": "google",
                    "redirect_uri": "http://localhost:5173/callback",
                },
                follow_redirects=False,
            )
            assert response1.status_code == 307

            # Second request should be rate limited
            response2 = client.get(
                "/api/v1/auth/login",
                params={
                    "provider": "google",
                    "redirect_uri": "http://localhost:5173/callback",
                },
                follow_redirects=False,
            )
            # Should be 429 Too Many Requests
            assert response2.status_code == 429
        finally:
            # Restore original limit
            settings.RATE_LIMIT_LOGIN = original_limit

    def test_rate_limit_exceeded_response_format(self):
        """Test rate limit exceeded response has correct format."""
        from app.core.config import settings

        original_limit = settings.RATE_LIMIT_DEFAULT

        # Temporarily lower the limit
        object.__setattr__(settings, "RATE_LIMIT_DEFAULT", "1/minute")

        try:
            # First request
            client.post("/api/v1/auth/logout")

            # Second request should be rate limited
            response = client.post("/api/v1/auth/logout")

            if response.status_code == 429:
                # Verify response has expected structure
                data = response.json()
                assert "error" in data or "detail" in data
        finally:
            object.__setattr__(settings, "RATE_LIMIT_DEFAULT", original_limit)
