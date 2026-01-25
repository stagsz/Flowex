"""Tests for project API endpoints."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from pydantic import BaseModel

from app.api.routes.projects import (
    ActivityItemResponse,
    ActivityListResponse,
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
    _ACTION_DISPLAY_MAP,
)
from app.models import AuditAction


class TestProjectModels:
    """Tests for project Pydantic models."""

    def test_project_response_model(self):
        """Test ProjectResponse model serialization."""
        response = ProjectResponse(
            id=str(uuid4()),
            organization_id=str(uuid4()),
            name="Test Project",
            description="A test project",
            is_archived=False,
            created_at=datetime.now(timezone.utc).isoformat(),
            updated_at=datetime.now(timezone.utc).isoformat(),
            drawing_count=5,
        )
        assert response.name == "Test Project"
        assert response.drawing_count == 5
        assert response.is_archived is False

    def test_project_response_default_drawing_count(self):
        """Test ProjectResponse model has default drawing_count of 0."""
        response = ProjectResponse(
            id=str(uuid4()),
            organization_id=str(uuid4()),
            name="Test Project",
            description=None,
            is_archived=False,
            created_at=datetime.now(timezone.utc).isoformat(),
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
        assert response.drawing_count == 0

    def test_project_create_model(self):
        """Test ProjectCreate model validation."""
        create = ProjectCreate(name="New Project", description="Description")
        assert create.name == "New Project"
        assert create.description == "Description"

    def test_project_create_optional_description(self):
        """Test ProjectCreate model with optional description."""
        create = ProjectCreate(name="New Project")
        assert create.name == "New Project"
        assert create.description is None

    def test_project_update_model(self):
        """Test ProjectUpdate model with partial fields."""
        update = ProjectUpdate(name="Updated Name")
        assert update.name == "Updated Name"
        assert update.description is None
        assert update.is_archived is None

    def test_project_update_all_fields(self):
        """Test ProjectUpdate model with all fields."""
        update = ProjectUpdate(
            name="Updated Name",
            description="Updated description",
            is_archived=True,
        )
        assert update.name == "Updated Name"
        assert update.description == "Updated description"
        assert update.is_archived is True


class TestProjectDrawingCount:
    """Tests for drawing_count functionality in projects."""

    def test_drawing_count_in_response(self):
        """Test that drawing_count is included in ProjectResponse."""
        response = ProjectResponse(
            id=str(uuid4()),
            organization_id=str(uuid4()),
            name="Project with Drawings",
            description="Has some drawings",
            is_archived=False,
            created_at=datetime.now(timezone.utc).isoformat(),
            updated_at=datetime.now(timezone.utc).isoformat(),
            drawing_count=10,
        )
        # Verify it's in the model dict
        model_dict = response.model_dump()
        assert "drawing_count" in model_dict
        assert model_dict["drawing_count"] == 10

    def test_drawing_count_zero_for_new_project(self):
        """Test that new projects have drawing_count of 0."""
        response = ProjectResponse(
            id=str(uuid4()),
            organization_id=str(uuid4()),
            name="Empty Project",
            description=None,
            is_archived=False,
            created_at=datetime.now(timezone.utc).isoformat(),
            updated_at=datetime.now(timezone.utc).isoformat(),
            drawing_count=0,
        )
        assert response.drawing_count == 0

    def test_drawing_count_large_number(self):
        """Test that drawing_count handles large numbers."""
        response = ProjectResponse(
            id=str(uuid4()),
            organization_id=str(uuid4()),
            name="Large Project",
            description="Many drawings",
            is_archived=False,
            created_at=datetime.now(timezone.utc).isoformat(),
            updated_at=datetime.now(timezone.utc).isoformat(),
            drawing_count=9999,
        )
        assert response.drawing_count == 9999


class TestActivityFeedModels:
    """Tests for activity feed Pydantic models (DB-09)."""

    def test_activity_item_response_model(self):
        """Test ActivityItemResponse model serialization."""
        response = ActivityItemResponse(
            id=str(uuid4()),
            user_name="Anna Müller",
            action="uploaded",
            entity_type="drawing",
            entity_name="P&ID-001 Rev A",
            timestamp=datetime.now(timezone.utc),
        )
        assert response.user_name == "Anna Müller"
        assert response.action == "uploaded"
        assert response.entity_type == "drawing"
        assert response.entity_name == "P&ID-001 Rev A"

    def test_activity_item_response_with_null_user(self):
        """Test ActivityItemResponse model with system user (null user_name)."""
        response = ActivityItemResponse(
            id=str(uuid4()),
            user_name=None,
            action="started_processing",
            entity_type="drawing",
            entity_name="P&ID-002",
            timestamp=datetime.now(timezone.utc),
        )
        assert response.user_name is None
        assert response.action == "started_processing"

    def test_activity_item_response_with_null_entity(self):
        """Test ActivityItemResponse model with null entity fields."""
        response = ActivityItemResponse(
            id=str(uuid4()),
            user_name="Erik",
            action="exported",
            entity_type=None,
            entity_name=None,
            timestamp=datetime.now(timezone.utc),
        )
        assert response.entity_type is None
        assert response.entity_name is None

    def test_activity_list_response_model(self):
        """Test ActivityListResponse model serialization."""
        item = ActivityItemResponse(
            id=str(uuid4()),
            user_name="Maria",
            action="completed_validation",
            entity_type="drawing",
            entity_name="P&ID-003",
            timestamp=datetime.now(timezone.utc),
        )
        response = ActivityListResponse(
            items=[item],
            total=1,
            limit=10,
        )
        assert len(response.items) == 1
        assert response.total == 1
        assert response.limit == 10

    def test_activity_list_response_empty(self):
        """Test ActivityListResponse model with empty items."""
        response = ActivityListResponse(
            items=[],
            total=0,
            limit=10,
        )
        assert len(response.items) == 0
        assert response.total == 0


class TestActionDisplayMap:
    """Tests for action display name mapping."""

    def test_drawing_upload_maps_to_uploaded(self):
        """Test DRAWING_UPLOAD maps to 'uploaded'."""
        assert _ACTION_DISPLAY_MAP[AuditAction.DRAWING_UPLOAD] == "uploaded"

    def test_drawing_process_maps_to_started_processing(self):
        """Test DRAWING_PROCESS maps to 'started_processing'."""
        assert _ACTION_DISPLAY_MAP[AuditAction.DRAWING_PROCESS] == "started_processing"

    def test_symbol_bulk_verify_maps_to_completed_validation(self):
        """Test SYMBOL_BULK_VERIFY maps to 'completed_validation'."""
        assert _ACTION_DISPLAY_MAP[AuditAction.SYMBOL_BULK_VERIFY] == "completed_validation"

    def test_export_actions_map_to_exported(self):
        """Test all export actions map to 'exported'."""
        assert _ACTION_DISPLAY_MAP[AuditAction.EXPORT_DXF] == "exported"
        assert _ACTION_DISPLAY_MAP[AuditAction.EXPORT_LIST] == "exported"
        assert _ACTION_DISPLAY_MAP[AuditAction.EXPORT_REPORT] == "exported"
        assert _ACTION_DISPLAY_MAP[AuditAction.EXPORT_CHECKLIST] == "exported"

    def test_project_actions_mapped(self):
        """Test project-level actions are mapped."""
        assert _ACTION_DISPLAY_MAP[AuditAction.PROJECT_CREATE] == "created_project"
        assert _ACTION_DISPLAY_MAP[AuditAction.PROJECT_UPDATE] == "updated_project"
        assert _ACTION_DISPLAY_MAP[AuditAction.PROJECT_DELETE] == "archived_project"

    def test_user_management_actions_mapped(self):
        """Test user management actions are mapped."""
        assert _ACTION_DISPLAY_MAP[AuditAction.USER_INVITE] == "invited_user"
        assert _ACTION_DISPLAY_MAP[AuditAction.USER_REMOVE] == "removed_user"

    def test_symbol_operations_mapped(self):
        """Test symbol operation actions are mapped."""
        assert _ACTION_DISPLAY_MAP[AuditAction.SYMBOL_CREATE] == "added_symbol"
        assert _ACTION_DISPLAY_MAP[AuditAction.SYMBOL_UPDATE] == "edited_symbol"
        assert _ACTION_DISPLAY_MAP[AuditAction.SYMBOL_DELETE] == "deleted_symbol"
        assert _ACTION_DISPLAY_MAP[AuditAction.SYMBOL_VERIFY] == "verified_symbol"
        assert _ACTION_DISPLAY_MAP[AuditAction.SYMBOL_FLAG] == "flagged_symbol"

    def test_line_operations_mapped(self):
        """Test line operation actions are mapped."""
        assert _ACTION_DISPLAY_MAP[AuditAction.LINE_CREATE] == "added_line"
        assert _ACTION_DISPLAY_MAP[AuditAction.LINE_UPDATE] == "edited_line"
        assert _ACTION_DISPLAY_MAP[AuditAction.LINE_DELETE] == "deleted_line"
        assert _ACTION_DISPLAY_MAP[AuditAction.LINE_VERIFY] == "verified_line"
        assert _ACTION_DISPLAY_MAP[AuditAction.LINE_BULK_VERIFY] == "verified_lines"
