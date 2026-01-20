"""Security headers middleware for FastAPI.

Implements OWASP recommended security headers to protect against common attacks:
- Clickjacking (X-Frame-Options)
- MIME type sniffing (X-Content-Type-Options)
- XSS attacks (X-XSS-Protection, Content-Security-Policy)
- Referrer leakage (Referrer-Policy)
- Feature abuse (Permissions-Policy)
- Protocol downgrade (Strict-Transport-Security)

References:
- https://owasp.org/www-project-secure-headers/
- https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers
"""

from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all responses."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Add security headers to the response."""
        response = await call_next(request)

        # Clickjacking protection - prevents page from being embedded in iframes
        # DENY = never allow, SAMEORIGIN = allow only from same origin
        response.headers["X-Frame-Options"] = settings.SECURITY_X_FRAME_OPTIONS

        # Prevent MIME type sniffing - browser should use declared Content-Type
        response.headers["X-Content-Type-Options"] = "nosniff"

        # XSS protection for legacy browsers (modern browsers use CSP)
        # 1; mode=block = enable filter and block page if XSS detected
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Control referrer information sent with requests
        # strict-origin-when-cross-origin = full URL for same-origin, origin only for cross-origin
        response.headers["Referrer-Policy"] = settings.SECURITY_REFERRER_POLICY

        # Permissions Policy (formerly Feature Policy) - restrict browser features
        # Disable features that are not needed for security
        response.headers["Permissions-Policy"] = settings.SECURITY_PERMISSIONS_POLICY

        # Content Security Policy - restrict resource loading
        # Only add if configured (CSP can break functionality if misconfigured)
        if settings.SECURITY_CSP_ENABLED and settings.SECURITY_CSP_DIRECTIVES:
            response.headers["Content-Security-Policy"] = settings.SECURITY_CSP_DIRECTIVES

        # HTTP Strict Transport Security - force HTTPS
        # Only add in production (requires valid HTTPS)
        if settings.SECURITY_HSTS_ENABLED:
            hsts_value = f"max-age={settings.SECURITY_HSTS_MAX_AGE}"
            if settings.SECURITY_HSTS_INCLUDE_SUBDOMAINS:
                hsts_value += "; includeSubDomains"
            if settings.SECURITY_HSTS_PRELOAD:
                hsts_value += "; preload"
            response.headers["Strict-Transport-Security"] = hsts_value

        # Cache control for sensitive endpoints (auth, user data)
        # Prevent caching of sensitive responses
        if self._is_sensitive_endpoint(request.url.path):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
            response.headers["Pragma"] = "no-cache"

        return response

    def _is_sensitive_endpoint(self, path: str) -> bool:
        """Check if the endpoint handles sensitive data.

        Args:
            path: The request URL path.

        Returns:
            True if the endpoint is sensitive and should not be cached.
        """
        sensitive_prefixes = (
            "/api/v1/auth/",
            "/api/v1/users/",
            "/api/v1/cloud/",
        )
        return path.startswith(sensitive_prefixes)
