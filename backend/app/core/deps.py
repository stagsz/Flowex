import logging
from collections.abc import Generator
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.security import TokenPayload, verify_token
from app.models import User, UserRole
from app.models.organization import Organization

logger = logging.getLogger(__name__)

# Security scheme - always auto_error=False so we control the response code (403 for missing credentials)
security = HTTPBearer(auto_error=False)


def get_db() -> Generator[Session, None, None]:
    """Database session dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_token_payload(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> TokenPayload:
    """Extract and verify token from Authorization header."""
    try:
        return await verify_token(credentials.credentials)
    except ValueError as e:
        # Log full error details for debugging
        logger.warning(f"Token verification failed: {e}")
        # In production, use generic error message to avoid leaking implementation details
        detail = str(e) if settings.DEBUG else "Invalid or expired token"
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


def _get_or_create_dev_user(db: Session) -> User:
    """Get or create a development user for auth bypass."""
    dev_email = "dev@flowex.local"
    user = db.query(User).filter(User.email == dev_email).first()

    # Try to use the first real organization (not dev-org) for better dev experience
    # This allows dev user to access existing projects
    real_org = db.query(Organization).filter(Organization.slug != "dev-org").first()

    if user:
        # Update dev user to use real org if available and different
        if real_org and user.organization_id != real_org.id:
            user.organization_id = real_org.id
            db.commit()
            db.refresh(user)
            logger.info(f"Updated dev user to organization: {real_org.name}")
        return user

    # Use real organization if available, otherwise create dev-org
    org: Organization
    if real_org:
        org = real_org
        logger.info(f"Dev user will use existing organization: {org.name}")
    else:
        # Create dev organization only if no real org exists
        existing_org = db.query(Organization).filter(Organization.slug == "dev-org").first()
        if existing_org:
            org = existing_org
        else:
            org = Organization(
                name="Dev Organization",
                slug="dev-org",
            )
            db.add(org)
            db.flush()
            logger.info("Created dev organization")

    # Create dev user
    user = User(
        email=dev_email,
        name="Dev User",
        role=UserRole.ADMIN,
        organization_id=org.id,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info(f"Created dev user in organization: {org.name}")
    return user


def _get_or_create_user(db: Session, token: TokenPayload) -> User:
    """Get or create a user from OAuth token (auto-provisioning for Supabase Auth)."""
    if not token.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token missing email claim",
        )

    # Look up existing user
    user = db.query(User).filter(User.email == token.email).first()
    if user:
        return user

    # Auto-provision new user on first login
    logger.info(f"Auto-provisioning new user: {token.email}")

    # Create organization based on email domain
    email_domain = token.email.split("@")[1] if "@" in token.email else "unknown"
    org_slug = email_domain.replace(".", "-").lower()
    org_name = email_domain.split(".")[0].capitalize()

    # Check if organization exists (by slug or create new)
    org = db.query(Organization).filter(Organization.slug == org_slug).first()
    if not org:
        org = Organization(
            name=f"{org_name} Organization",
            slug=org_slug,
        )
        db.add(org)
        db.flush()
        logger.info(f"Created organization: {org.name} ({org.slug})")

    # Create user - first user in org becomes admin
    existing_org_users = db.query(User).filter(User.organization_id == org.id).count()
    user_role = UserRole.ADMIN if existing_org_users == 0 else UserRole.MEMBER

    user = User(
        email=token.email,
        name=token.name or token.email.split("@")[0],
        role=user_role,
        organization_id=org.id,
        sso_subject_id=token.sub,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info(f"Created user: {user.email} (role: {user_role.value})")
    return user


async def get_current_user(
    db: Annotated[Session, Depends(get_db)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)] = None,
) -> User:
    """Get the current authenticated user."""
    # Dev auth bypass for local development
    if settings.DEBUG and settings.DEV_AUTH_BYPASS:
        logger.warning("DEV_AUTH_BYPASS active - using dev user")
        return _get_or_create_dev_user(db)

    # Normal auth flow
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authenticated",
        )

    try:
        token = await verify_token(credentials.credentials)
    except ValueError as e:
        logger.warning(f"Token verification failed: {e}")
        detail = str(e) if settings.DEBUG else "Invalid or expired token"
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        ) from e

    # Get or create user (auto-provisioning for OAuth users)
    user = _get_or_create_user(db, token)

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive",
        )
    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Alias for get_current_user (already checks is_active)."""
    return current_user


class RoleChecker:
    """Dependency for checking user roles."""

    def __init__(self, allowed_roles: list[UserRole]):
        self.allowed_roles = allowed_roles

    def __call__(self, user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user


# Role-based dependencies
require_admin = RoleChecker([UserRole.ADMIN])
require_member = RoleChecker([UserRole.ADMIN, UserRole.MEMBER])
require_viewer = RoleChecker([UserRole.ADMIN, UserRole.MEMBER, UserRole.VIEWER])


class OrganizationChecker:
    """Dependency for checking organization access."""

    def __call__(
        self,
        organization_id: UUID,
        user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        if user.organization_id != organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this organization",
            )
        return user


require_org_access = OrganizationChecker()
