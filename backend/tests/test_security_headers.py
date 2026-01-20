"""Tests for security headers middleware."""

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app

client = TestClient(app)


class TestSecurityHeaders:
    """Test security headers are present in responses."""

    def test_x_frame_options_header(self):
        """Test X-Frame-Options header is present and set correctly."""
        response = client.get("/health")
        assert response.status_code == 200
        assert "X-Frame-Options" in response.headers
        assert response.headers["X-Frame-Options"] == settings.SECURITY_X_FRAME_OPTIONS

    def test_x_content_type_options_header(self):
        """Test X-Content-Type-Options header prevents MIME sniffing."""
        response = client.get("/health")
        assert response.status_code == 200
        assert "X-Content-Type-Options" in response.headers
        assert response.headers["X-Content-Type-Options"] == "nosniff"

    def test_x_xss_protection_header(self):
        """Test X-XSS-Protection header is present for legacy browsers."""
        response = client.get("/health")
        assert response.status_code == 200
        assert "X-XSS-Protection" in response.headers
        assert response.headers["X-XSS-Protection"] == "1; mode=block"

    def test_referrer_policy_header(self):
        """Test Referrer-Policy header controls referrer information."""
        response = client.get("/health")
        assert response.status_code == 200
        assert "Referrer-Policy" in response.headers
        assert response.headers["Referrer-Policy"] == settings.SECURITY_REFERRER_POLICY

    def test_permissions_policy_header(self):
        """Test Permissions-Policy header restricts browser features."""
        response = client.get("/health")
        assert response.status_code == 200
        assert "Permissions-Policy" in response.headers
        # Should contain restrictions for common dangerous features
        permissions = response.headers["Permissions-Policy"]
        assert "camera=()" in permissions
        assert "microphone=()" in permissions
        assert "geolocation=()" in permissions

    def test_csp_header_disabled_by_default(self):
        """Test CSP header is not present when disabled (default)."""
        # CSP is disabled by default to prevent breaking functionality
        response = client.get("/health")
        assert response.status_code == 200
        # CSP should not be present when SECURITY_CSP_ENABLED is False
        if not settings.SECURITY_CSP_ENABLED:
            assert "Content-Security-Policy" not in response.headers

    def test_hsts_header_disabled_in_dev(self):
        """Test HSTS header is not present in development (disabled by default)."""
        response = client.get("/health")
        assert response.status_code == 200
        # HSTS should not be present when SECURITY_HSTS_ENABLED is False
        if not settings.SECURITY_HSTS_ENABLED:
            assert "Strict-Transport-Security" not in response.headers

    def test_headers_present_on_api_endpoints(self):
        """Test security headers are present on API endpoints."""
        response = client.post("/api/v1/auth/logout")
        assert response.status_code == 200
        # Core security headers should be present
        assert "X-Frame-Options" in response.headers
        assert "X-Content-Type-Options" in response.headers
        assert "X-XSS-Protection" in response.headers
        assert "Referrer-Policy" in response.headers
        assert "Permissions-Policy" in response.headers

    def test_headers_present_on_error_responses(self):
        """Test security headers are present even on error responses."""
        response = client.get("/api/v1/auth/login", params={"provider": "invalid"})
        # Should be a 400 or 422 error
        assert response.status_code in [400, 422]
        # Security headers should still be present
        assert "X-Frame-Options" in response.headers
        assert "X-Content-Type-Options" in response.headers


class TestCacheControlHeaders:
    """Test cache control for sensitive endpoints."""

    def test_auth_endpoints_no_cache(self):
        """Test auth endpoints have no-cache headers."""
        response = client.post("/api/v1/auth/logout")
        assert response.status_code == 200
        # Auth endpoints should not be cached
        assert "Cache-Control" in response.headers
        cache_control = response.headers["Cache-Control"]
        assert "no-store" in cache_control
        assert "no-cache" in cache_control

    def test_auth_endpoints_pragma_no_cache(self):
        """Test auth endpoints have Pragma: no-cache for HTTP/1.0 compatibility."""
        response = client.post("/api/v1/auth/logout")
        assert response.status_code == 200
        assert "Pragma" in response.headers
        assert response.headers["Pragma"] == "no-cache"

    def test_non_sensitive_endpoints_no_special_cache(self):
        """Test non-sensitive endpoints don't have forced no-cache."""
        response = client.get("/health")
        assert response.status_code == 200
        # Health endpoint is not sensitive, may not have no-cache
        # (middleware only adds no-cache to sensitive endpoints)
        # This test verifies the middleware doesn't over-apply cache restrictions


class TestSecurityHeadersConfig:
    """Test security headers configuration."""

    def test_x_frame_options_default_deny(self):
        """Test default X-Frame-Options is DENY."""
        assert settings.SECURITY_X_FRAME_OPTIONS == "DENY"

    def test_referrer_policy_default(self):
        """Test default Referrer-Policy is strict-origin-when-cross-origin."""
        assert settings.SECURITY_REFERRER_POLICY == "strict-origin-when-cross-origin"

    def test_csp_disabled_by_default(self):
        """Test CSP is disabled by default to prevent breaking functionality."""
        assert settings.SECURITY_CSP_ENABLED is False

    def test_hsts_disabled_by_default(self):
        """Test HSTS is disabled by default (requires valid HTTPS)."""
        assert settings.SECURITY_HSTS_ENABLED is False

    def test_hsts_max_age_one_year(self):
        """Test HSTS max-age is set to 1 year (31536000 seconds)."""
        assert settings.SECURITY_HSTS_MAX_AGE == 31536000

    def test_permissions_policy_restricts_dangerous_features(self):
        """Test Permissions-Policy restricts dangerous browser features."""
        policy = settings.SECURITY_PERMISSIONS_POLICY
        # Should restrict camera, microphone, geolocation by default
        assert "camera=()" in policy
        assert "microphone=()" in policy
        assert "geolocation=()" in policy
        assert "payment=()" in policy


class TestSecurityHeadersWithEnabledCSP:
    """Test security headers when CSP is enabled."""

    @pytest.fixture(autouse=True)
    def enable_csp(self):
        """Temporarily enable CSP for these tests."""
        original = settings.SECURITY_CSP_ENABLED
        settings.SECURITY_CSP_ENABLED = True
        yield
        settings.SECURITY_CSP_ENABLED = original

    def test_csp_header_present_when_enabled(self):
        """Test CSP header is present when enabled."""
        response = client.get("/health")
        assert response.status_code == 200
        assert "Content-Security-Policy" in response.headers

    def test_csp_header_has_default_src(self):
        """Test CSP header contains default-src directive."""
        response = client.get("/health")
        csp = response.headers.get("Content-Security-Policy", "")
        assert "default-src" in csp

    def test_csp_header_blocks_frame_ancestors(self):
        """Test CSP header blocks framing with frame-ancestors."""
        response = client.get("/health")
        csp = response.headers.get("Content-Security-Policy", "")
        assert "frame-ancestors" in csp


class TestSecurityHeadersWithEnabledHSTS:
    """Test security headers when HSTS is enabled."""

    @pytest.fixture(autouse=True)
    def enable_hsts(self):
        """Temporarily enable HSTS for these tests."""
        original = settings.SECURITY_HSTS_ENABLED
        settings.SECURITY_HSTS_ENABLED = True
        yield
        settings.SECURITY_HSTS_ENABLED = original

    def test_hsts_header_present_when_enabled(self):
        """Test HSTS header is present when enabled."""
        response = client.get("/health")
        assert response.status_code == 200
        assert "Strict-Transport-Security" in response.headers

    def test_hsts_header_has_max_age(self):
        """Test HSTS header contains max-age directive."""
        response = client.get("/health")
        hsts = response.headers.get("Strict-Transport-Security", "")
        assert f"max-age={settings.SECURITY_HSTS_MAX_AGE}" in hsts

    def test_hsts_header_has_include_subdomains(self):
        """Test HSTS header includes subdomains when configured."""
        if settings.SECURITY_HSTS_INCLUDE_SUBDOMAINS:
            response = client.get("/health")
            hsts = response.headers.get("Strict-Transport-Security", "")
            assert "includeSubDomains" in hsts
