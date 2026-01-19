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

logger = logging.getLogger(__name__)

# Security scheme
security = HTTPBearer()


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


async def get_current_user(
    db: Annotated[Session, Depends(get_db)],
    token: Annotated[TokenPayload, Depends(get_token_payload)],
) -> User:
    """Get the current authenticated user."""
    user = db.query(User).filter(User.email == token.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
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
