from typing import Annotated
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_current_user, get_db
from app.models import Organization, SSOProvider, User

router = APIRouter(prefix="/auth", tags=["authentication"])


def _is_valid_redirect_uri(redirect_uri: str) -> bool:
    """Validate redirect URI against allowed origins to prevent open redirect attacks."""
    # Allow configured CORS origins
    allowed_origins = settings.CORS_ORIGINS

    # Check if redirect_uri starts with any allowed origin
    for origin in allowed_origins:
        if redirect_uri.startswith(origin):
            return True

    return False


class UserResponse(BaseModel):
    id: str
    email: str
    name: str | None
    role: str
    organization_id: str
    organization_name: str

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: str | None = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str


@router.get("/login")
async def login(
    provider: str = Query(..., description="SSO provider: 'microsoft' or 'google'"),
    redirect_uri: str = Query(..., description="URI to redirect after login"),
) -> RedirectResponse:
    """Initiate SSO login flow."""
    if provider not in ["microsoft", "google"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid provider. Use 'microsoft' or 'google'",
        )

    # Validate redirect URI to prevent open redirect attacks
    if not _is_valid_redirect_uri(redirect_uri):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid redirect URI. Must match allowed origins.",
        )

    # Build Auth0 authorization URL
    params = {
        "client_id": settings.AUTH0_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": "openid profile email",
        "connection": "google-oauth2" if provider == "google" else "windowslive",
    }
    auth_url = f"https://{settings.AUTH0_DOMAIN}/authorize?{urlencode(params)}"
    return RedirectResponse(url=auth_url)


@router.get("/callback")
async def callback(
    code: str = Query(..., description="Authorization code from Auth0"),
    redirect_uri: str = Query(..., description="Original redirect URI"),
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Handle OAuth callback and exchange code for tokens."""
    # Validate redirect URI to prevent token theft via open redirect
    if not _is_valid_redirect_uri(redirect_uri):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid redirect URI. Must match allowed origins.",
        )

    # Exchange code for tokens
    token_url = f"https://{settings.AUTH0_DOMAIN}/oauth/token"
    async with httpx.AsyncClient() as client:
        response = await client.post(
            token_url,
            json={
                "grant_type": "authorization_code",
                "client_id": settings.AUTH0_CLIENT_ID,
                "client_secret": settings.AUTH0_CLIENT_SECRET,
                "code": code,
                "redirect_uri": redirect_uri,
            },
        )
        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Failed to exchange authorization code",
            )
        tokens = response.json()

    # Get user info from Auth0
    userinfo_url = f"https://{settings.AUTH0_DOMAIN}/userinfo"
    async with httpx.AsyncClient() as client:
        response = await client.get(
            userinfo_url,
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Failed to get user info",
            )
        userinfo = response.json()

    # Find or create user
    email = userinfo.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email not provided by SSO provider",
        )

    user = db.query(User).filter(User.email == email).first()
    if not user:
        # Create organization and user for new users
        org_name = email.split("@")[1].split(".")[0].title()
        org_slug = email.split("@")[1].replace(".", "-").lower()

        # Check if org exists
        org = db.query(Organization).filter(Organization.slug == org_slug).first()
        if not org:
            org = Organization(name=org_name, slug=org_slug)
            db.add(org)
            db.flush()

        # Determine SSO provider
        sub = userinfo.get("sub", "")
        sso_provider = SSOProvider.GOOGLE if "google" in sub else SSOProvider.MICROSOFT

        user = User(
            email=email,
            name=userinfo.get("name"),
            organization_id=org.id,
            sso_provider=sso_provider,
            sso_subject_id=sub,
        )
        db.add(user)
        db.commit()

    return TokenResponse(
        access_token=tokens["access_token"],
        expires_in=tokens.get("expires_in", 86400),
        refresh_token=tokens.get("refresh_token"),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshTokenRequest) -> TokenResponse:
    """Refresh access token using a refresh token from Auth0."""
    token_url = f"https://{settings.AUTH0_DOMAIN}/oauth/token"

    async with httpx.AsyncClient() as client:
        response = await client.post(
            token_url,
            json={
                "grant_type": "refresh_token",
                "client_id": settings.AUTH0_CLIENT_ID,
                "client_secret": settings.AUTH0_CLIENT_SECRET,
                "refresh_token": request.refresh_token,
            },
        )
        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
            )
        tokens = response.json()

    return TokenResponse(
        access_token=tokens["access_token"],
        expires_in=tokens.get("expires_in", 86400),
        refresh_token=tokens.get("refresh_token"),
    )


@router.post("/logout")
async def logout() -> dict[str, str]:
    """Logout the current user."""
    # For JWT-based auth, logout is handled client-side by deleting the token
    # Optionally, we could implement token blacklisting here
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserResponse:
    """Get the current authenticated user's information."""
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        name=current_user.name,
        role=current_user.role.value,
        organization_id=str(current_user.organization_id),
        organization_name=current_user.organization.name,
    )
