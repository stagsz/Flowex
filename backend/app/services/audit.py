"""Audit logging service for tracking user activity (SEC-04 compliance)."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import Request
from sqlalchemy.orm import Session

from app.models.audit_log import AuditAction, AuditLog, EntityType
from app.models.user import User


def get_client_ip(request: Request) -> str | None:
    """Extract client IP address from request, handling proxies."""
    # Check for X-Forwarded-For header (common for load balancers/proxies)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # First IP in the list is the original client
        return forwarded_for.split(",")[0].strip()

    # Check for X-Real-IP header (nginx)
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    # Fall back to direct client IP
    if request.client:
        return request.client.host

    return None


def get_user_agent(request: Request) -> str | None:
    """Extract user agent from request."""
    user_agent = request.headers.get("User-Agent")
    if user_agent:
        # Truncate to 500 chars (db column limit)
        return user_agent[:500]
    return None


def log_action(
    db: Session,
    user: User | None,
    organization_id: UUID,
    action: AuditAction,
    request: Request | None = None,
    entity_type: EntityType | None = None,
    entity_id: UUID | None = None,
    metadata: dict[str, Any] | None = None,
) -> AuditLog:
    """Log a user action to the audit log.

    Args:
        db: Database session
        user: The user performing the action (None if not authenticated)
        organization_id: Organization context for the action
        action: The type of action being performed
        request: Optional FastAPI request for IP/user-agent extraction
        entity_type: Optional type of entity being acted upon
        entity_id: Optional ID of the entity being acted upon
        metadata: Optional additional context as JSON

    Returns:
        The created AuditLog entry
    """
    ip_address = None
    user_agent = None

    if request:
        ip_address = get_client_ip(request)
        user_agent = get_user_agent(request)

    audit_log = AuditLog(
        user_id=user.id if user else None,
        organization_id=organization_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        ip_address=ip_address,
        user_agent=user_agent,
        extra_data=metadata,
        timestamp=datetime.now(UTC),
    )

    db.add(audit_log)
    # Note: Caller should commit the transaction
    # This allows audit log to be part of the same transaction as the action

    return audit_log


def log_action_background(
    db: Session,
    user_id: UUID | None,
    organization_id: UUID,
    action: AuditAction,
    entity_type: EntityType | None = None,
    entity_id: UUID | None = None,
    metadata: dict[str, Any] | None = None,
) -> AuditLog:
    """Log an action from a background task (no request context).

    Args:
        db: Database session
        user_id: The user ID performing the action (None if not authenticated)
        organization_id: Organization context for the action
        action: The type of action being performed
        entity_type: Optional type of entity being acted upon
        entity_id: Optional ID of the entity being acted upon
        metadata: Optional additional context as JSON

    Returns:
        The created AuditLog entry
    """
    audit_log = AuditLog(
        user_id=user_id,
        organization_id=organization_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        ip_address=None,
        user_agent=None,
        extra_data=metadata,
        timestamp=datetime.now(UTC),
    )

    db.add(audit_log)
    return audit_log
