from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from jose import JWTError, jwt
from pydantic import BaseModel

from app.core.config import settings


class TokenPayload(BaseModel):
    sub: str
    exp: datetime
    iat: datetime
    email: str | None = None
    name: str | None = None
    org_id: str | None = None
    role: str | None = None


class Auth0JWKSClient:
    """Client to fetch and cache Auth0 JWKS (JSON Web Key Set)."""

    def __init__(self, domain: str):
        self.domain = domain
        self.jwks_uri = f"https://{domain}/.well-known/jwks.json"
        self._jwks: dict[str, Any] | None = None
        self._jwks_fetched_at: datetime | None = None
        self._cache_duration = timedelta(hours=1)

    async def get_signing_key(self, kid: str) -> dict[str, Any] | None:
        """Get the signing key for the given key ID."""
        jwks = await self._get_jwks()
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                return key
        return None

    async def _get_jwks(self) -> dict[str, Any]:
        """Fetch JWKS from Auth0, with caching."""
        now = datetime.now(timezone.utc)
        if (
            self._jwks is not None
            and self._jwks_fetched_at is not None
            and now - self._jwks_fetched_at < self._cache_duration
        ):
            return self._jwks

        async with httpx.AsyncClient() as client:
            response = await client.get(self.jwks_uri)
            response.raise_for_status()
            self._jwks = response.json()
            self._jwks_fetched_at = now
            return self._jwks


# Global JWKS client instance
_jwks_client: Auth0JWKSClient | None = None


def get_jwks_client() -> Auth0JWKSClient:
    """Get or create the JWKS client."""
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = Auth0JWKSClient(settings.AUTH0_DOMAIN)
    return _jwks_client


async def verify_token(token: str) -> TokenPayload:
    """Verify and decode a JWT token from Auth0."""
    try:
        # Decode header to get key ID
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        if not kid:
            raise JWTError("Token missing key ID")

        # Get signing key from JWKS
        jwks_client = get_jwks_client()
        signing_key = await jwks_client.get_signing_key(kid)
        if not signing_key:
            raise JWTError("Unable to find signing key")

        # Verify and decode token
        payload = jwt.decode(
            token,
            signing_key,
            algorithms=[settings.JWT_ALGORITHM],
            audience=settings.AUTH0_CLIENT_ID,
            issuer=f"https://{settings.AUTH0_DOMAIN}/",
        )

        return TokenPayload(
            sub=payload["sub"],
            exp=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
            iat=datetime.fromtimestamp(payload["iat"], tz=timezone.utc),
            email=payload.get("email"),
            name=payload.get("name"),
            org_id=payload.get("org_id"),
            role=payload.get("role"),
        )

    except JWTError as e:
        raise ValueError(f"Invalid token: {e}") from e


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token (for internal use/testing)."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(hours=settings.ACCESS_TOKEN_EXPIRE_HOURS))
    to_encode.update({"exp": expire, "iat": now})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm="HS256")
