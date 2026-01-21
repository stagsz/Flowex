from datetime import UTC, datetime, timedelta
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
                result: dict[str, Any] = key
                return result
        return None

    async def _get_jwks(self) -> dict[str, Any]:
        """Fetch JWKS from Auth0, with caching."""
        now = datetime.now(UTC)
        if (
            self._jwks is not None
            and self._jwks_fetched_at is not None
            and now - self._jwks_fetched_at < self._cache_duration
        ):
            return self._jwks

        async with httpx.AsyncClient() as client:
            response = await client.get(self.jwks_uri)
            response.raise_for_status()
            jwks: dict[str, Any] = response.json()
            self._jwks = jwks
            self._jwks_fetched_at = now
            return self._jwks


# Global JWKS client instance (for Auth0)
_jwks_client: Auth0JWKSClient | None = None


def get_jwks_client() -> Auth0JWKSClient:
    """Get or create the JWKS client."""
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = Auth0JWKSClient(settings.AUTH0_DOMAIN)
    return _jwks_client


class SupabaseJWKSClient:
    """Client to fetch and cache Supabase JWKS (JSON Web Key Set)."""

    def __init__(self, supabase_url: str):
        self.supabase_url = supabase_url.rstrip("/")
        self.jwks_uri = f"{self.supabase_url}/auth/v1/.well-known/jwks.json"
        self._jwks: dict[str, Any] | None = None
        self._jwks_fetched_at: datetime | None = None
        self._cache_duration = timedelta(hours=1)

    async def get_signing_key(self, kid: str) -> dict[str, Any] | None:
        """Get the signing key for the given key ID."""
        jwks = await self._get_jwks()
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                result: dict[str, Any] = key
                return result
        return None

    async def _get_jwks(self) -> dict[str, Any]:
        """Fetch JWKS from Supabase, with caching."""
        now = datetime.now(UTC)
        if (
            self._jwks is not None
            and self._jwks_fetched_at is not None
            and now - self._jwks_fetched_at < self._cache_duration
        ):
            return self._jwks

        async with httpx.AsyncClient() as client:
            response = await client.get(self.jwks_uri)
            response.raise_for_status()
            jwks: dict[str, Any] = response.json()
            self._jwks = jwks
            self._jwks_fetched_at = now
            return self._jwks


# Global Supabase JWKS client instance
_supabase_jwks_client: SupabaseJWKSClient | None = None


def get_supabase_jwks_client() -> SupabaseJWKSClient:
    """Get or create the Supabase JWKS client."""
    global _supabase_jwks_client
    if _supabase_jwks_client is None:
        _supabase_jwks_client = SupabaseJWKSClient(settings.SUPABASE_URL)
    return _supabase_jwks_client


async def verify_supabase_token(token: str) -> TokenPayload:
    """Verify and decode a JWT token from Supabase Auth."""
    try:
        # Get the unverified header to check algorithm and key ID
        unverified_header = jwt.get_unverified_header(token)
        alg = unverified_header.get("alg")
        kid = unverified_header.get("kid")

        if alg == "ES256" and kid:
            # ES256: Use JWKS to get public key (for OAuth tokens)
            jwks_client = get_supabase_jwks_client()
            signing_key = await jwks_client.get_signing_key(kid)
            if not signing_key:
                raise JWTError("Unable to find signing key for Supabase token")

            payload = jwt.decode(
                token,
                signing_key,
                algorithms=["ES256"],
                audience="authenticated",
            )
        elif alg == "HS256":
            # HS256: Use JWT secret (for service tokens)
            jwt_secret = settings.SUPABASE_JWT_SECRET
            if not jwt_secret:
                raise JWTError("SUPABASE_JWT_SECRET not configured")

            payload = jwt.decode(
                token,
                jwt_secret,
                algorithms=["HS256"],
                audience="authenticated",
            )
        else:
            raise JWTError(f"Unsupported algorithm: {alg}")

        # Extract user metadata from Supabase token structure
        # Supabase tokens have: sub, email, role, aud, exp, iat
        # User metadata is in user_metadata or app_metadata
        user_metadata = payload.get("user_metadata", {})
        app_metadata = payload.get("app_metadata", {})

        return TokenPayload(
            sub=payload["sub"],
            exp=datetime.fromtimestamp(payload["exp"], tz=UTC),
            iat=datetime.fromtimestamp(payload["iat"], tz=UTC),
            email=payload.get("email"),
            name=user_metadata.get("name") or user_metadata.get("full_name"),
            org_id=app_metadata.get("org_id"),
            role=app_metadata.get("role") or payload.get("role"),
        )

    except JWTError as e:
        raise ValueError(f"Invalid Supabase token: {e}") from e


async def verify_auth0_token(token: str) -> TokenPayload:
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
            algorithms=["RS256"],
            audience=settings.AUTH0_CLIENT_ID,
            issuer=f"https://{settings.AUTH0_DOMAIN}/",
        )

        return TokenPayload(
            sub=payload["sub"],
            exp=datetime.fromtimestamp(payload["exp"], tz=UTC),
            iat=datetime.fromtimestamp(payload["iat"], tz=UTC),
            email=payload.get("email"),
            name=payload.get("name"),
            org_id=payload.get("org_id"),
            role=payload.get("role"),
        )

    except JWTError as e:
        raise ValueError(f"Invalid Auth0 token: {e}") from e


async def verify_token(token: str) -> TokenPayload:
    """Verify and decode a JWT token based on configured auth provider."""
    if settings.AUTH_PROVIDER == "supabase":
        return await verify_supabase_token(token)
    else:
        return await verify_auth0_token(token)


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token (for internal use/testing)."""
    to_encode = data.copy()
    now = datetime.now(UTC)
    expire = now + (expires_delta or timedelta(hours=settings.ACCESS_TOKEN_EXPIRE_HOURS))
    to_encode.update({"exp": expire, "iat": now})
    # Use HS256 for internal tokens
    encoded: str = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm="HS256")
    return encoded
