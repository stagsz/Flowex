"""Organization management endpoints including user/team management."""

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db, require_admin
from app.core.rate_limiting import default_limit, limiter
from app.models import Organization, User, UserRole
from app.models.organization_invite import InviteStatus, OrganizationInvite

router = APIRouter(prefix="/organizations", tags=["organizations"])


# =============================================================================
# Request/Response Models
# =============================================================================


class UserResponse(BaseModel):
    """User information for organization member lists."""

    id: str
    email: str
    name: str | None
    role: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserListResponse(BaseModel):
    """Paginated list of organization users."""

    items: list[UserResponse]
    total: int
    page: int
    page_size: int


class InviteUserRequest(BaseModel):
    """Request to invite a user to the organization."""

    email: EmailStr = Field(..., description="Email address to invite")
    role: UserRole = Field(default=UserRole.MEMBER, description="Role to assign")


class InviteResponse(BaseModel):
    """Response for a created invitation."""

    id: str
    email: str
    role: str
    status: str
    expires_at: datetime
    created_at: datetime
    invited_by_name: str | None = None

    model_config = ConfigDict(from_attributes=True)


class InviteListResponse(BaseModel):
    """Paginated list of organization invitations."""

    items: list[InviteResponse]
    total: int
    page: int
    page_size: int


class UpdateUserRoleRequest(BaseModel):
    """Request to update a user's role."""

    role: UserRole = Field(..., description="New role for the user")


class AcceptInviteRequest(BaseModel):
    """Request to accept an invitation."""

    token: str = Field(..., description="Invitation token")


class AcceptInviteResponse(BaseModel):
    """Response after accepting an invitation."""

    message: str
    organization_name: str
    role: str


class OrganizationUsageResponse(BaseModel):
    """Organization usage statistics (for billing/usage tracking)."""

    organization_id: str
    organization_name: str
    period_start: datetime
    period_end: datetime
    plan: str
    plan_limit: int
    used_count: int
    remaining_count: int
    member_count: int


# =============================================================================
# Helper Functions
# =============================================================================


def _serialize_user(user: User) -> UserResponse:
    """Serialize a user for API response."""
    return UserResponse(
        id=str(user.id),
        email=user.email,
        name=user.name,
        role=user.role.value,
        is_active=user.is_active,
        created_at=user.created_at,
    )


def _serialize_invite(invite: OrganizationInvite) -> InviteResponse:
    """Serialize an invite for API response."""
    return InviteResponse(
        id=str(invite.id),
        email=invite.email,
        role=invite.role.value,
        status=invite.status.value,
        expires_at=invite.expires_at,
        created_at=invite.created_at,
        invited_by_name=invite.invited_by.name if invite.invited_by else None,
    )


# =============================================================================
# User Management Endpoints
# =============================================================================


@router.get("/{organization_id}/users", response_model=UserListResponse)
@limiter.limit(default_limit)
async def list_organization_users(
    request: Request,
    organization_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    include_inactive: bool = Query(False, description="Include deactivated users"),
) -> UserListResponse:
    """List all users in the organization.

    Returns a paginated list of organization members.
    All organization members can view the user list.
    """
    # Verify access to organization
    if current_user.organization_id != organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this organization",
        )

    # Build query
    query = db.query(User).filter(User.organization_id == organization_id)

    if not include_inactive:
        query = query.filter(User.is_active.is_(True))

    # Get total count
    total = query.count()

    # Get paginated results
    users = (
        query.order_by(User.created_at)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return UserListResponse(
        items=[_serialize_user(u) for u in users],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.patch(
    "/{organization_id}/users/{user_id}",
    response_model=UserResponse,
)
@limiter.limit(default_limit)
async def update_user_role(
    request: Request,
    organization_id: UUID,
    user_id: UUID,
    body: UpdateUserRoleRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
) -> UserResponse:
    """Update a user's role in the organization.

    Admin only. Allows changing user roles (admin, member, viewer).
    Cannot change own role (prevents accidental lockout).
    """
    # Verify access to organization
    if current_user.organization_id != organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this organization",
        )

    # Prevent self-demotion
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change your own role",
        )

    # Find target user
    target_user = db.query(User).filter(
        User.id == user_id,
        User.organization_id == organization_id,
    ).first()

    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in this organization",
        )

    # Update role
    target_user.role = body.role
    db.commit()
    db.refresh(target_user)

    return _serialize_user(target_user)


@router.delete(
    "/{organization_id}/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
@limiter.limit(default_limit)
async def remove_user(
    request: Request,
    organization_id: UUID,
    user_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
) -> None:
    """Remove a user from the organization.

    Admin only. Deactivates the user account (soft delete).
    Cannot remove yourself - use account deletion instead.
    """
    # Verify access to organization
    if current_user.organization_id != organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this organization",
        )

    # Cannot remove yourself
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove yourself. Use account deletion instead.",
        )

    # Find target user
    target_user = db.query(User).filter(
        User.id == user_id,
        User.organization_id == organization_id,
    ).first()

    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in this organization",
        )

    # Deactivate user (soft delete)
    target_user.is_active = False
    db.commit()


# =============================================================================
# Invitation Endpoints
# =============================================================================


@router.post(
    "/{organization_id}/invites",
    response_model=InviteResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit(default_limit)
async def invite_user(
    request: Request,
    organization_id: UUID,
    body: InviteUserRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
) -> InviteResponse:
    """Invite a user to join the organization.

    Admin only. Creates a pending invitation that can be accepted
    by the invited user within 7 days.

    If the user already exists in the system with a different organization,
    they cannot be invited (users belong to one organization).
    """
    # Verify access to organization
    if current_user.organization_id != organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this organization",
        )

    # Check if email is already registered
    existing_user = db.query(User).filter(User.email == body.email).first()
    if existing_user:
        if existing_user.organization_id == organization_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already a member of this organization",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already belongs to another organization",
        )

    # Check for existing pending invite
    existing_invite = db.query(OrganizationInvite).filter(
        OrganizationInvite.organization_id == organization_id,
        OrganizationInvite.email == body.email,
        OrganizationInvite.status == InviteStatus.PENDING,
    ).first()

    if existing_invite and existing_invite.is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A pending invitation already exists for this email",
        )

    # Create invitation
    invite = OrganizationInvite(
        organization_id=organization_id,
        email=body.email,
        role=body.role,
        invited_by_id=current_user.id,
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)

    # Note: In production, send invitation email here
    # For beta, just return the token which can be shared manually

    return _serialize_invite(invite)


@router.get("/{organization_id}/invites", response_model=InviteListResponse)
@limiter.limit(default_limit)
async def list_invites(
    request: Request,
    organization_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: InviteStatus | None = Query(None, alias="status"),
) -> InviteListResponse:
    """List all invitations for the organization.

    Admin only. Returns pending, accepted, expired, and revoked invitations.
    """
    # Verify access to organization
    if current_user.organization_id != organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this organization",
        )

    # Build query
    query = db.query(OrganizationInvite).filter(
        OrganizationInvite.organization_id == organization_id
    )

    if status_filter:
        query = query.filter(OrganizationInvite.status == status_filter)

    # Get total count
    total = query.count()

    # Get paginated results
    invites = (
        query.order_by(desc(OrganizationInvite.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return InviteListResponse(
        items=[_serialize_invite(i) for i in invites],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.delete(
    "/{organization_id}/invites/{invite_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
@limiter.limit(default_limit)
async def revoke_invite(
    request: Request,
    organization_id: UUID,
    invite_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
) -> None:
    """Revoke a pending invitation.

    Admin only. Cannot revoke already accepted invitations.
    """
    # Verify access to organization
    if current_user.organization_id != organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this organization",
        )

    # Find invitation
    invite = db.query(OrganizationInvite).filter(
        OrganizationInvite.id == invite_id,
        OrganizationInvite.organization_id == organization_id,
    ).first()

    if not invite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found",
        )

    if invite.status == InviteStatus.ACCEPTED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot revoke an accepted invitation",
        )

    invite.status = InviteStatus.REVOKED
    db.commit()


@router.post("/invites/accept", response_model=AcceptInviteResponse)
@limiter.limit(default_limit)
async def accept_invite(
    request: Request,
    body: AcceptInviteRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> AcceptInviteResponse:
    """Accept an invitation to join an organization.

    The invitation token is provided in the request body.
    The user accepting must be authenticated (via SSO) and their
    email must match the invitation email.
    """
    # Find the invitation by token
    invite = db.query(OrganizationInvite).filter(
        OrganizationInvite.token == body.token
    ).first()

    if not invite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid invitation token",
        )

    # Check if invitation is still valid
    if invite.status != InviteStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invitation is no longer valid (status: {invite.status.value})",
        )

    if invite.is_expired:
        invite.status = InviteStatus.EXPIRED
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation has expired",
        )

    # Verify email matches
    if current_user.email.lower() != invite.email.lower():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This invitation was sent to a different email address",
        )

    # Get the organization
    org = db.query(Organization).filter(
        Organization.id == invite.organization_id
    ).first()

    if not org:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Organization not found",
        )

    # Update user's organization and role
    current_user.organization_id = invite.organization_id
    current_user.role = invite.role

    # Mark invitation as accepted
    invite.status = InviteStatus.ACCEPTED
    invite.accepted_at = datetime.now(UTC)

    db.commit()

    return AcceptInviteResponse(
        message="Successfully joined organization",
        organization_name=org.name,
        role=invite.role.value,
    )


# =============================================================================
# Usage/Stats Endpoints
# =============================================================================


@router.get("/{organization_id}/usage", response_model=OrganizationUsageResponse)
@limiter.limit(default_limit)
async def get_organization_usage(
    request: Request,
    organization_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> OrganizationUsageResponse:
    """Get organization usage statistics.

    Returns current period usage, plan limits, and member count.
    All organization members can view usage (for dashboard display).
    """
    # Verify access to organization
    if current_user.organization_id != organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this organization",
        )

    # Get organization
    org = db.query(Organization).filter(Organization.id == organization_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    # Get member count
    member_count = db.query(User).filter(
        User.organization_id == organization_id,
        User.is_active.is_(True),
    ).count()

    # Calculate current billing period (monthly)
    now = datetime.now(UTC)
    period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if now.month == 12:
        period_end = period_start.replace(year=now.year + 1, month=1)
    else:
        period_end = period_start.replace(month=now.month + 1)

    return OrganizationUsageResponse(
        organization_id=str(org.id),
        organization_name=org.name,
        period_start=period_start,
        period_end=period_end,
        plan=org.subscription_tier.value,
        plan_limit=org.monthly_pid_limit,
        used_count=org.pids_used_this_month,
        remaining_count=max(0, org.monthly_pid_limit - org.pids_used_this_month),
        member_count=member_count,
    )
