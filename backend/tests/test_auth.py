from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.main import app

client = TestClient(app)


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
