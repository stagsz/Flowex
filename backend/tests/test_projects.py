"""Tests for project API endpoints."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from pydantic import BaseModel

from app.api.routes.projects import ProjectCreate, ProjectResponse, ProjectUpdate


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
