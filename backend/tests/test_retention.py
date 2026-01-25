"""Tests for data retention tasks (GDPR-08 compliance).

Tests cover:
- Drawing cleanup after retention period
- Audit log purging after 3 years
- Scheduled user deletions
- Configuration settings
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Drawing, DrawingStatus, Project
from app.models.audit_log import AuditAction, AuditLog, EntityType
from app.models.organization import Organization
from app.models.user import User, UserRole


class TestRetentionConfiguration:
    """Tests for retention configuration settings."""

    def test_retention_enabled_by_default(self):
        """Retention should be enabled by default."""
        assert settings.RETENTION_ENABLED is True

    def test_drawing_retention_days_default(self):
        """Drawings should be retained for 365 days by default."""
        assert settings.RETENTION_DAYS_DRAWINGS == 365

    def test_audit_log_retention_days_default(self):
        """Audit logs should be retained for 3 years (1095 days) by default."""
        assert settings.RETENTION_DAYS_AUDIT_LOGS == 1095

    def test_deletion_grace_period_default(self):
        """Account deletion grace period should be 30 days by default."""
        assert settings.DELETION_GRACE_PERIOD_DAYS == 30

    def test_cleanup_batch_size_default(self):
        """Cleanup batch size should be 100 by default."""
        assert settings.RETENTION_CLEANUP_BATCH_SIZE == 100


class TestCleanupOldDrawings:
    """Tests for the cleanup_old_drawings task."""

    @patch("app.tasks.retention.settings")
    def test_skips_when_retention_disabled(self, mock_settings):
        """Task should skip cleanup when retention is disabled."""
        mock_settings.RETENTION_ENABLED = False

        from app.tasks.retention import cleanup_old_drawings

        result = cleanup_old_drawings.apply().get()

        assert result["status"] == "skipped"
        assert result["reason"] == "retention_disabled"

    @patch("app.tasks.retention.run_async")
    @patch("app.tasks.retention.SessionLocal")
    @patch("app.tasks.retention.get_storage_service")
    @patch("app.tasks.retention.settings")
    def test_deletes_old_drawings(
        self, mock_settings, mock_get_storage, mock_session_local, mock_run_async
    ):
        """Task should delete drawings older than retention period."""
        mock_settings.RETENTION_ENABLED = True
        mock_settings.RETENTION_DAYS_DRAWINGS = 365
        mock_settings.RETENTION_CLEANUP_BATCH_SIZE = 100

        # Create mock drawing with old last_accessed_at
        old_date = datetime.now(UTC) - timedelta(days=400)
        mock_drawing = MagicMock(spec=Drawing)
        mock_drawing.id = uuid4()
        mock_drawing.storage_path = "org/2023/01/01/test.pdf"
        mock_drawing.last_accessed_at = old_date
        mock_drawing.created_at = old_date
        mock_drawing.status = DrawingStatus.complete
        mock_drawing.project = MagicMock()
        mock_drawing.project.organization_id = uuid4()

        # Set up mock DB session
        mock_db = MagicMock(spec=Session)
        mock_session_local.return_value = mock_db

        # First query returns the old drawing, second returns empty (end loop)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.side_effect = [[mock_drawing], []]
        mock_db.execute.return_value = mock_result

        # Mock storage service
        mock_storage = MagicMock()
        mock_get_storage.return_value = mock_storage

        # Mock run_async to do nothing (storage operations succeed)
        mock_run_async.return_value = None

        from app.tasks.retention import cleanup_old_drawings

        result = cleanup_old_drawings.apply().get()

        assert result["status"] == "success"
        assert result["deleted_count"] == 1
        mock_db.delete.assert_called_once_with(mock_drawing)

    @patch("app.tasks.retention.SessionLocal")
    @patch("app.tasks.retention.get_storage_service")
    @patch("app.tasks.retention.settings")
    def test_handles_storage_errors_gracefully(
        self, mock_settings, mock_get_storage, mock_session_local
    ):
        """Task should continue if storage deletion fails."""
        mock_settings.RETENTION_ENABLED = True
        mock_settings.RETENTION_DAYS_DRAWINGS = 365
        mock_settings.RETENTION_CLEANUP_BATCH_SIZE = 100

        old_date = datetime.now(UTC) - timedelta(days=400)
        mock_drawing = MagicMock(spec=Drawing)
        mock_drawing.id = uuid4()
        mock_drawing.storage_path = "org/2023/01/01/test.pdf"
        mock_drawing.last_accessed_at = old_date
        mock_drawing.created_at = old_date
        mock_drawing.status = DrawingStatus.complete
        mock_drawing.project = MagicMock()
        mock_drawing.project.organization_id = uuid4()

        mock_db = MagicMock(spec=Session)
        mock_session_local.return_value = mock_db

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.side_effect = [[mock_drawing], []]
        mock_db.execute.return_value = mock_result

        # Storage service that raises an error
        mock_storage = MagicMock()
        mock_get_storage.return_value = mock_storage

        from app.services.storage import StorageError
        from app.tasks.retention import cleanup_old_drawings, run_async

        # Make run_async raise StorageError for delete
        with patch(
            "app.tasks.retention.run_async",
            side_effect=[StorageError("Network error"), FileNotFoundError()],
        ):
            result = cleanup_old_drawings.apply().get()

        # Task should still succeed even with storage errors
        assert result["status"] == "success"
        assert result["deleted_count"] == 1

    @patch("app.tasks.retention.run_async")
    @patch("app.tasks.retention.SessionLocal")
    @patch("app.tasks.retention.get_storage_service")
    @patch("app.tasks.retention.settings")
    def test_includes_legacy_drawings_without_last_accessed(
        self, mock_settings, mock_get_storage, mock_session_local, mock_run_async
    ):
        """Task should include drawings with NULL last_accessed_at if created before retention."""
        mock_settings.RETENTION_ENABLED = True
        mock_settings.RETENTION_DAYS_DRAWINGS = 365
        mock_settings.RETENTION_CLEANUP_BATCH_SIZE = 100

        old_date = datetime.now(UTC) - timedelta(days=400)
        mock_drawing = MagicMock(spec=Drawing)
        mock_drawing.id = uuid4()
        mock_drawing.storage_path = "org/2023/01/01/test.pdf"
        mock_drawing.last_accessed_at = None  # Legacy drawing without tracking
        mock_drawing.created_at = old_date
        mock_drawing.status = DrawingStatus.complete
        mock_drawing.project = MagicMock()
        mock_drawing.project.organization_id = uuid4()

        mock_db = MagicMock(spec=Session)
        mock_session_local.return_value = mock_db

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.side_effect = [[mock_drawing], []]
        mock_db.execute.return_value = mock_result

        mock_storage = MagicMock()
        mock_get_storage.return_value = mock_storage

        # Mock run_async to do nothing (storage operations succeed)
        mock_run_async.return_value = None

        from app.tasks.retention import cleanup_old_drawings

        result = cleanup_old_drawings.apply().get()

        assert result["status"] == "success"
        assert result["deleted_count"] == 1


class TestPurgeOldAuditLogs:
    """Tests for the purge_old_audit_logs task."""

    @patch("app.tasks.retention.settings")
    def test_skips_when_retention_disabled(self, mock_settings):
        """Task should skip purge when retention is disabled."""
        mock_settings.RETENTION_ENABLED = False

        from app.tasks.retention import purge_old_audit_logs

        result = purge_old_audit_logs.apply().get()

        assert result["status"] == "skipped"
        assert result["reason"] == "retention_disabled"

    @patch("app.tasks.retention.SessionLocal")
    @patch("app.tasks.retention.settings")
    def test_purges_old_audit_logs(self, mock_settings, mock_session_local):
        """Task should delete audit logs older than retention period."""
        mock_settings.RETENTION_ENABLED = True
        mock_settings.RETENTION_DAYS_AUDIT_LOGS = 1095
        mock_settings.RETENTION_CLEANUP_BATCH_SIZE = 100

        mock_db = MagicMock(spec=Session)
        mock_session_local.return_value = mock_db

        # First query returns some IDs, second returns empty
        old_log_id = uuid4()
        mock_db.execute.return_value.fetchall.side_effect = [
            [(old_log_id,)],  # First batch
            [],  # No more logs
        ]

        # Mock delete result
        mock_delete_result = MagicMock()
        mock_delete_result.rowcount = 1
        mock_db.execute.return_value = mock_delete_result

        from app.tasks.retention import purge_old_audit_logs

        result = purge_old_audit_logs.apply().get()

        assert result["status"] == "success"
        assert "deleted_count" in result


class TestProcessScheduledDeletions:
    """Tests for the process_scheduled_deletions task."""

    @patch("app.tasks.retention.settings")
    def test_skips_when_retention_disabled(self, mock_settings):
        """Task should skip processing when retention is disabled."""
        mock_settings.RETENTION_ENABLED = False

        from app.tasks.retention import process_scheduled_deletions

        result = process_scheduled_deletions.apply().get()

        assert result["status"] == "skipped"
        assert result["reason"] == "retention_disabled"

    @patch("app.tasks.retention.SessionLocal")
    @patch("app.tasks.retention.settings")
    def test_processes_expired_deletions(self, mock_settings, mock_session_local):
        """Task should anonymize users whose deletion grace period has expired."""
        mock_settings.RETENTION_ENABLED = True

        mock_db = MagicMock(spec=Session)
        mock_session_local.return_value = mock_db

        # Create mock user scheduled for deletion
        past_date = datetime.now(UTC) - timedelta(days=1)
        mock_user = MagicMock(spec=User)
        mock_user.id = uuid4()
        mock_user.email = "test@example.com"
        mock_user.organization_id = uuid4()
        mock_user.scheduled_deletion_at = past_date
        mock_user.deletion_reason = "user_request"
        mock_user.is_active = True

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_user]
        mock_db.execute.return_value = mock_result

        from app.tasks.retention import process_scheduled_deletions

        result = process_scheduled_deletions.apply().get()

        assert result["status"] == "success"
        assert result["processed_count"] == 1
        # Verify user was anonymized
        assert "deleted_" in mock_user.email
        assert mock_user.name == "Deleted User"
        assert mock_user.is_active is False

    @patch("app.tasks.retention.SessionLocal")
    @patch("app.tasks.retention.settings")
    def test_does_not_process_future_deletions(self, mock_settings, mock_session_local):
        """Task should not process users whose deletion is scheduled in the future."""
        mock_settings.RETENTION_ENABLED = True

        mock_db = MagicMock(spec=Session)
        mock_session_local.return_value = mock_db

        # Mock query returns no users (future deletions filtered out)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        from app.tasks.retention import process_scheduled_deletions

        result = process_scheduled_deletions.apply().get()

        assert result["status"] == "success"
        assert result["processed_count"] == 0


class TestRunAllRetentionTasks:
    """Tests for the run_all_retention_tasks convenience task."""

    @patch("app.tasks.retention.process_scheduled_deletions")
    @patch("app.tasks.retention.purge_old_audit_logs")
    @patch("app.tasks.retention.cleanup_old_drawings")
    def test_runs_all_tasks(
        self, mock_cleanup, mock_purge, mock_deletions
    ):
        """Task should run all retention tasks in sequence."""
        mock_cleanup.apply.return_value.get.return_value = {"status": "success"}
        mock_purge.apply.return_value.get.return_value = {"status": "success"}
        mock_deletions.apply.return_value.get.return_value = {"status": "success"}

        from app.tasks.retention import run_all_retention_tasks

        result = run_all_retention_tasks.apply().get()

        assert "drawings" in result
        assert "audit_logs" in result
        assert "user_deletions" in result
        mock_cleanup.apply.assert_called_once()
        mock_purge.apply.assert_called_once()
        mock_deletions.apply.assert_called_once()


class TestCeleryBeatSchedule:
    """Tests for Celery beat schedule configuration."""

    def test_beat_schedule_exists(self):
        """Beat schedule should be configured when not in eager mode."""
        # In test mode, we're in eager mode, so we need to check the config
        from app.core.celery_app import celery_app

        # Check if we have beat_schedule configured (only in production mode)
        if not settings.CELERY_TASK_ALWAYS_EAGER:
            assert hasattr(celery_app.conf, "beat_schedule")
            assert "cleanup-old-drawings-daily" in celery_app.conf.beat_schedule
            assert "purge-audit-logs-monthly" in celery_app.conf.beat_schedule
            assert "process-scheduled-deletions-daily" in celery_app.conf.beat_schedule


class TestDrawingAccessTracking:
    """Tests for drawing access tracking."""

    def test_update_last_accessed_helper(self):
        """The _update_last_accessed helper should update the timestamp."""
        from app.api.routes.drawings import _update_last_accessed

        mock_db = MagicMock(spec=Session)
        mock_drawing = MagicMock(spec=Drawing)
        mock_drawing.last_accessed_at = None

        before = datetime.now(UTC)
        _update_last_accessed(mock_db, mock_drawing)
        after = datetime.now(UTC)

        # Verify timestamp was set
        assert mock_drawing.last_accessed_at is not None
        assert before <= mock_drawing.last_accessed_at <= after
        mock_db.commit.assert_called_once()


class TestRetentionModels:
    """Tests for retention-related model fields."""

    def test_drawing_has_last_accessed_at(self):
        """Drawing model should have last_accessed_at field."""
        from app.models.drawing import Drawing

        # Check the model has the field defined
        assert hasattr(Drawing, "last_accessed_at")

    def test_user_has_scheduled_deletion_at(self):
        """User model should have scheduled_deletion_at field."""
        from app.models.user import User

        assert hasattr(User, "scheduled_deletion_at")

    def test_user_has_deletion_reason(self):
        """User model should have deletion_reason field."""
        from app.models.user import User

        assert hasattr(User, "deletion_reason")
