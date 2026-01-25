"""Data retention tasks for GDPR-08 compliance.

Implements automated data lifecycle management:
- Archive/delete drawings after 1 year since last access
- Purge audit logs older than 3 years
- Process scheduled account deletions after grace period

Per GDPR Article 5(1)(e) - Storage Limitation principle.
"""

import asyncio
import logging
from collections.abc import Coroutine
from datetime import UTC, datetime, timedelta
from typing import Any, TypeVar

from sqlalchemy import and_, delete, select
from sqlalchemy.orm import Session

from app.core.celery_app import celery_app
from app.core.config import settings
from app.core.database import SessionLocal
from app.models import Drawing, DrawingStatus
from app.models.audit_log import AuditAction, AuditLog, EntityType
from app.models.user import User
from app.services.storage import StorageError, get_storage_service

logger = logging.getLogger(__name__)

T = TypeVar("T")


def run_async(coro: Coroutine[Any, Any, T]) -> T:
    """Run an async coroutine, handling both eager mode and normal mode."""
    try:
        asyncio.get_running_loop()
        import nest_asyncio  # type: ignore[import-untyped]

        nest_asyncio.apply()
        return asyncio.run(coro)
    except RuntimeError:
        return asyncio.run(coro)


def _log_retention_action(
    db: Session,
    action: AuditAction,
    entity_type: EntityType,
    entity_id: Any,
    organization_id: Any,
    extra_data: dict[str, Any] | None = None,
) -> None:
    """Log a retention action to the audit log."""
    log_entry = AuditLog(
        user_id=None,  # System action, no user
        organization_id=organization_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        ip_address="system",
        user_agent="retention-task",
        extra_data=extra_data or {},
        timestamp=datetime.now(UTC),
    )
    db.add(log_entry)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=300)  # type: ignore[misc]
def cleanup_old_drawings(self: Any) -> dict[str, Any]:
    """Archive/delete drawings that haven't been accessed within the retention period.

    Per GDPR-08 spec: Drawings are archived/deleted after 1 year since last access.

    Process:
    1. Find drawings where last_accessed_at < (now - retention_days)
    2. Delete associated files from storage
    3. Hard delete the drawing record

    Returns:
        Dict with cleanup results including counts of deleted drawings and any errors.
    """
    if not settings.RETENTION_ENABLED:
        logger.info("Data retention is disabled, skipping cleanup")
        return {"status": "skipped", "reason": "retention_disabled"}

    db: Session = SessionLocal()
    storage = get_storage_service()

    cutoff_date = datetime.now(UTC) - timedelta(days=settings.RETENTION_DAYS_DRAWINGS)
    batch_size = settings.RETENTION_CLEANUP_BATCH_SIZE

    deleted_count = 0
    error_count = 0
    errors: list[dict[str, str]] = []

    try:
        logger.info(
            f"Starting drawing cleanup for drawings last accessed before {cutoff_date}"
        )

        while True:
            # Find drawings older than retention period
            # Also include drawings with NULL last_accessed_at if they were created
            # before the retention period (legacy data)
            stmt = (
                select(Drawing)
                .where(
                    and_(
                        Drawing.status.in_(
                            [DrawingStatus.complete, DrawingStatus.error]
                        ),
                        (
                            (Drawing.last_accessed_at < cutoff_date)
                            | (
                                (Drawing.last_accessed_at.is_(None))
                                & (Drawing.created_at < cutoff_date)
                            )
                        ),
                    )
                )
                .limit(batch_size)
            )
            drawings = db.execute(stmt).scalars().all()

            if not drawings:
                break

            for drawing in drawings:
                try:
                    # Delete files from storage
                    if drawing.storage_path:
                        try:
                            run_async(storage.delete_file(drawing.storage_path))
                        except (StorageError, FileNotFoundError) as e:
                            logger.warning(
                                f"Failed to delete storage file for drawing {drawing.id}: {e}"
                            )

                        # Also delete processed images if they exist
                        base_path = drawing.storage_path.rsplit("/", 1)[0]
                        try:
                            run_async(
                                storage.delete_file(f"{base_path}/processed/page_1.png")
                            )
                        except (StorageError, FileNotFoundError):
                            pass  # Processed files may not exist

                    # Get organization_id before deleting
                    project = drawing.project
                    org_id = project.organization_id if project else None

                    # Log the deletion
                    if org_id:
                        _log_retention_action(
                            db,
                            AuditAction.DRAWING_DELETE,
                            EntityType.DRAWING,
                            drawing.id,
                            org_id,
                            {
                                "reason": "retention_policy",
                                "last_accessed_at": (
                                    drawing.last_accessed_at.isoformat()
                                    if drawing.last_accessed_at
                                    else None
                                ),
                                "created_at": drawing.created_at.isoformat(),
                            },
                        )

                    # Hard delete the drawing (cascades to symbols, lines, etc.)
                    db.delete(drawing)
                    deleted_count += 1

                except Exception as e:
                    logger.error(f"Error deleting drawing {drawing.id}: {e}")
                    errors.append({"drawing_id": str(drawing.id), "error": str(e)})
                    error_count += 1

            db.commit()
            logger.info(f"Deleted batch of {len(drawings)} drawings")

        db.commit()
        result = {
            "status": "success",
            "deleted_count": deleted_count,
            "error_count": error_count,
            "cutoff_date": cutoff_date.isoformat(),
            "errors": errors[:10] if errors else [],  # Limit error list size
        }
        logger.info(f"Drawing cleanup completed: {result}")
        return result

    except Exception as e:
        logger.error(f"Drawing cleanup failed: {e}")
        db.rollback()
        raise self.retry(exc=e)

    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=300)  # type: ignore[misc]
def purge_old_audit_logs(self: Any) -> dict[str, Any]:
    """Purge audit logs older than the retention period.

    Per GDPR-08 spec: Audit logs are retained for 3 years, then permanently deleted.

    Returns:
        Dict with purge results including count of deleted logs.
    """
    if not settings.RETENTION_ENABLED:
        logger.info("Data retention is disabled, skipping audit log purge")
        return {"status": "skipped", "reason": "retention_disabled"}

    db: Session = SessionLocal()

    cutoff_date = datetime.now(UTC) - timedelta(days=settings.RETENTION_DAYS_AUDIT_LOGS)
    batch_size = settings.RETENTION_CLEANUP_BATCH_SIZE

    total_deleted = 0

    try:
        logger.info(f"Starting audit log purge for logs older than {cutoff_date}")

        while True:
            # For batch deletion, we use a subquery approach
            # to avoid locking the entire table
            subquery = (
                select(AuditLog.id)
                .where(AuditLog.timestamp < cutoff_date)
                .limit(batch_size)
            )
            ids_to_delete = [row[0] for row in db.execute(subquery).fetchall()]

            if not ids_to_delete:
                break

            delete_stmt = delete(AuditLog).where(AuditLog.id.in_(ids_to_delete))
            db.execute(delete_stmt)
            deleted_count = len(ids_to_delete)  # Use batch size since delete was successful

            db.commit()
            total_deleted += deleted_count
            logger.info(f"Purged batch of {deleted_count} audit logs")

        result_dict = {
            "status": "success",
            "deleted_count": total_deleted,
            "cutoff_date": cutoff_date.isoformat(),
        }
        logger.info(f"Audit log purge completed: {result_dict}")
        return result_dict

    except Exception as e:
        logger.error(f"Audit log purge failed: {e}")
        db.rollback()
        raise self.retry(exc=e)

    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=300)  # type: ignore[misc]
def process_scheduled_deletions(self: Any) -> dict[str, Any]:
    """Process users scheduled for account deletion after grace period.

    Per GDPR Article 17 (Right to Erasure) with grace period for user safety.
    Users have DELETION_GRACE_PERIOD_DAYS to cancel deletion request.

    Process:
    1. Find users where scheduled_deletion_at < now
    2. Anonymize user data (keep structure for audit integrity)
    3. Delete associated personal data

    Returns:
        Dict with deletion results including count of processed users.
    """
    if not settings.RETENTION_ENABLED:
        logger.info("Data retention is disabled, skipping scheduled deletions")
        return {"status": "skipped", "reason": "retention_disabled"}

    db: Session = SessionLocal()

    now = datetime.now(UTC)

    processed_count = 0
    error_count = 0
    errors: list[dict[str, str]] = []

    try:
        logger.info("Processing scheduled account deletions")

        # Find users whose deletion grace period has expired
        stmt = select(User).where(
            and_(
                User.scheduled_deletion_at.is_not(None),
                User.scheduled_deletion_at <= now,
                User.is_active.is_(True),  # Not already deactivated
            )
        )
        users_to_delete = db.execute(stmt).scalars().all()

        for user in users_to_delete:
            try:
                org_id = user.organization_id

                # Log the deletion before anonymizing
                _log_retention_action(
                    db,
                    AuditAction.ACCOUNT_DELETION_REQUEST,
                    EntityType.USER,
                    user.id,
                    org_id,
                    {
                        "action": "completed",
                        "reason": user.deletion_reason or "user_request",
                        "scheduled_at": user.scheduled_deletion_at.isoformat()
                        if user.scheduled_deletion_at
                        else None,
                    },
                )

                # Anonymize user data (keep record for audit trail integrity)
                user.email = f"deleted_{user.id}@anonymized.local"
                user.name = "Deleted User"
                user.sso_subject_id = None
                user.is_active = False
                user.scheduled_deletion_at = None
                user.deletion_reason = None

                processed_count += 1
                logger.info(f"Processed deletion for user {user.id}")

            except Exception as e:
                logger.error(f"Error processing deletion for user {user.id}: {e}")
                errors.append({"user_id": str(user.id), "error": str(e)})
                error_count += 1

        db.commit()

        result = {
            "status": "success",
            "processed_count": processed_count,
            "error_count": error_count,
            "errors": errors[:10] if errors else [],
        }
        logger.info(f"Scheduled deletions completed: {result}")
        return result

    except Exception as e:
        logger.error(f"Scheduled deletion processing failed: {e}")
        db.rollback()
        raise self.retry(exc=e)

    finally:
        db.close()


@celery_app.task  # type: ignore[misc]
def run_all_retention_tasks() -> dict[str, Any]:
    """Run all retention tasks in sequence.

    This is a convenience task that runs:
    1. cleanup_old_drawings
    2. purge_old_audit_logs
    3. process_scheduled_deletions

    Returns:
        Combined results from all tasks.
    """
    results: dict[str, Any] = {}

    try:
        results["drawings"] = cleanup_old_drawings.apply().get()
    except Exception as e:
        results["drawings"] = {"status": "error", "error": str(e)}

    try:
        results["audit_logs"] = purge_old_audit_logs.apply().get()
    except Exception as e:
        results["audit_logs"] = {"status": "error", "error": str(e)}

    try:
        results["user_deletions"] = process_scheduled_deletions.apply().get()
    except Exception as e:
        results["user_deletions"] = {"status": "error", "error": str(e)}

    return results
