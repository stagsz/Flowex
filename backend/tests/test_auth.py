from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.main import app

client = TestClient(app)


def test_login_redirect_google():
    """Test login redirects to Auth0 for Google SSO."""
    response = client.get(
        "/api/v1/auth/login",
        params={"provider": "google", "redirect_uri": "http://localhost:5173/callback"},
        follow_redirects=False,
    )
    assert response.status_code == 307
    assert "authorize" in response.headers["location"]
    assert "google-oauth2" in response.headers["location"]


def test_login_redirect_microsoft():
    """Test login redirects to Auth0 for Microsoft SSO."""
    response = client.get(
        "/api/v1/auth/login",
        params={"provider": "microsoft", "redirect_uri": "http://localhost:5173/callback"},
        follow_redirects=False,
    )
    assert response.status_code == 307
    assert "authorize" in response.headers["location"]
    assert "windowslive" in response.headers["location"]


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
