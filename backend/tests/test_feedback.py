"""Tests for beta feedback API endpoints."""

import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import (
    BetaFeedback,
    FeedbackPriority,
    FeedbackStatus,
    FeedbackType,
    User,
    UserRole,
)


client = TestClient(app)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_admin_user():
    """Create a mock admin user."""
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.email = "admin@test.com"
    user.name = "Test Admin"
    user.organization_id = uuid.uuid4()
    user.role = UserRole.ADMIN
    user.is_active = True
    return user


@pytest.fixture
def mock_member_user():
    """Create a mock member user."""
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.email = "member@test.com"
    user.name = "Test Member"
    user.organization_id = uuid.uuid4()
    user.role = UserRole.MEMBER
    user.is_active = True
    return user


@pytest.fixture
def mock_feedback(mock_member_user):
    """Create a mock feedback item."""
    feedback = MagicMock(spec=BetaFeedback)
    feedback.id = uuid.uuid4()
    feedback.user_id = mock_member_user.id
    feedback.organization_id = mock_member_user.organization_id
    feedback.drawing_id = None
    feedback.feedback_type = FeedbackType.GENERAL
    feedback.priority = FeedbackPriority.MEDIUM
    feedback.title = "Test Feedback"
    feedback.description = "This is a test feedback description."
    feedback.page_url = "https://flowex.io/validation/123"
    feedback.user_agent = "Mozilla/5.0"
    feedback.screen_size = "1920x1080"
    feedback.satisfaction_rating = 4
    feedback.status = FeedbackStatus.NEW
    feedback.resolution_notes = None
    feedback.resolved_at = None
    feedback.created_at = datetime.now(UTC)
    feedback.updated_at = datetime.now(UTC)
    return feedback


# =============================================================================
# Model Tests
# =============================================================================


class TestFeedbackEnums:
    """Test feedback enum values."""

    def test_feedback_type_values(self):
        """Test FeedbackType enum has all expected values."""
        assert FeedbackType.BUG.value == "bug"
        assert FeedbackType.FEATURE_REQUEST.value == "feature_request"
        assert FeedbackType.USABILITY.value == "usability"
        assert FeedbackType.PERFORMANCE.value == "performance"
        assert FeedbackType.GENERAL.value == "general"

    def test_feedback_priority_values(self):
        """Test FeedbackPriority enum has all expected values."""
        assert FeedbackPriority.LOW.value == "low"
        assert FeedbackPriority.MEDIUM.value == "medium"
        assert FeedbackPriority.HIGH.value == "high"
        assert FeedbackPriority.CRITICAL.value == "critical"

    def test_feedback_status_values(self):
        """Test FeedbackStatus enum has all expected values."""
        assert FeedbackStatus.NEW.value == "new"
        assert FeedbackStatus.ACKNOWLEDGED.value == "acknowledged"
        assert FeedbackStatus.IN_PROGRESS.value == "in_progress"
        assert FeedbackStatus.RESOLVED.value == "resolved"
        assert FeedbackStatus.WONT_FIX.value == "wont_fix"


# =============================================================================
# API Endpoint Tests (Mocked)
# =============================================================================


class TestCreateFeedback:
    """Tests for POST /api/v1/feedback endpoint."""

    def test_create_feedback_unauthenticated(self):
        """Test that unauthenticated requests are rejected."""
        response = client.post(
            "/api/v1/feedback",
            json={
                "title": "Test Feedback",
                "description": "This is a test feedback.",
            },
        )
        # Should return 401 or 403 without valid auth
        assert response.status_code in (401, 403)

    def test_create_feedback_payload_validation(self):
        """Test that invalid payloads are rejected."""
        # Missing required fields - should fail validation
        response = client.post(
            "/api/v1/feedback",
            json={},
        )
        # Should return 401/403 (auth) or 422 (validation)
        assert response.status_code in (401, 403, 422)


class TestListFeedback:
    """Tests for GET /api/v1/feedback endpoint."""

    def test_list_feedback_unauthenticated(self):
        """Test that unauthenticated requests are rejected."""
        response = client.get("/api/v1/feedback")
        assert response.status_code in (401, 403)


class TestFeedbackStats:
    """Tests for GET /api/v1/feedback/stats endpoint."""

    def test_get_stats_unauthenticated(self):
        """Test that unauthenticated requests are rejected."""
        response = client.get("/api/v1/feedback/stats")
        assert response.status_code in (401, 403)


class TestUpdateFeedbackStatus:
    """Tests for PATCH /api/v1/feedback/{id}/status endpoint."""

    def test_update_status_unauthenticated(self):
        """Test that unauthenticated requests are rejected."""
        feedback_id = uuid.uuid4()
        response = client.patch(
            f"/api/v1/feedback/{feedback_id}/status",
            json={"status": "acknowledged"},
        )
        assert response.status_code in (401, 403)


class TestDeleteFeedback:
    """Tests for DELETE /api/v1/feedback/{id} endpoint."""

    def test_delete_feedback_unauthenticated(self):
        """Test that unauthenticated requests are rejected."""
        feedback_id = uuid.uuid4()
        response = client.delete(f"/api/v1/feedback/{feedback_id}")
        assert response.status_code in (401, 403)


# =============================================================================
# Request/Response Model Tests
# =============================================================================


class TestFeedbackRequestModels:
    """Tests for feedback request/response models."""

    def test_feedback_create_model_valid(self):
        """Test FeedbackCreate model with valid data."""
        from app.api.routes.feedback import FeedbackCreate

        data = FeedbackCreate(
            feedback_type=FeedbackType.BUG,
            priority=FeedbackPriority.HIGH,
            title="Bug in validation",
            description="The validation interface crashes when...",
            page_url="https://flowex.io/validation/123",
            satisfaction_rating=3,
        )

        assert data.feedback_type == FeedbackType.BUG
        assert data.priority == FeedbackPriority.HIGH
        assert data.title == "Bug in validation"
        assert data.satisfaction_rating == 3

    def test_feedback_create_model_defaults(self):
        """Test FeedbackCreate model default values."""
        from app.api.routes.feedback import FeedbackCreate

        data = FeedbackCreate(
            title="Simple feedback",
            description="A simple test feedback description.",
        )

        assert data.feedback_type == FeedbackType.GENERAL
        assert data.priority == FeedbackPriority.MEDIUM
        assert data.drawing_id is None
        assert data.satisfaction_rating is None

    def test_feedback_create_model_validation(self):
        """Test FeedbackCreate model validation constraints."""
        from pydantic import ValidationError

        from app.api.routes.feedback import FeedbackCreate

        # Title too short
        with pytest.raises(ValidationError):
            FeedbackCreate(title="AB", description="Valid description here")

        # Description too short
        with pytest.raises(ValidationError):
            FeedbackCreate(title="Valid title", description="Short")

        # Invalid satisfaction rating
        with pytest.raises(ValidationError):
            FeedbackCreate(
                title="Valid title",
                description="Valid description text",
                satisfaction_rating=6,  # Must be 1-5
            )

    def test_feedback_response_model(self):
        """Test FeedbackResponse model."""
        from app.api.routes.feedback import FeedbackResponse

        now = datetime.now(UTC)
        data = FeedbackResponse(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            organization_id=uuid.uuid4(),
            drawing_id=None,
            feedback_type=FeedbackType.FEATURE_REQUEST,
            priority=FeedbackPriority.LOW,
            title="Add dark mode",
            description="Would be nice to have a dark mode option.",
            page_url=None,
            user_agent=None,
            screen_size=None,
            satisfaction_rating=5,
            status=FeedbackStatus.ACKNOWLEDGED,
            resolution_notes="Added to backlog",
            resolved_at=None,
            created_at=now,
            updated_at=now,
        )

        assert data.feedback_type == FeedbackType.FEATURE_REQUEST
        assert data.status == FeedbackStatus.ACKNOWLEDGED
        assert data.resolution_notes == "Added to backlog"

    def test_feedback_stats_model(self):
        """Test FeedbackStats model."""
        from app.api.routes.feedback import FeedbackStats

        stats = FeedbackStats(
            total_feedback=100,
            by_type={"bug": 30, "feature_request": 40, "general": 30},
            by_status={"new": 50, "acknowledged": 30, "resolved": 20},
            by_priority={"low": 20, "medium": 50, "high": 25, "critical": 5},
            average_satisfaction=4.2,
            recent_feedback_count=15,
        )

        assert stats.total_feedback == 100
        assert stats.by_type["bug"] == 30
        assert stats.average_satisfaction == 4.2
        assert stats.recent_feedback_count == 15

    def test_feedback_status_update_model(self):
        """Test FeedbackStatusUpdate model."""
        from app.api.routes.feedback import FeedbackStatusUpdate

        update = FeedbackStatusUpdate(
            status=FeedbackStatus.RESOLVED,
            resolution_notes="Fixed in version 1.2.0",
        )

        assert update.status == FeedbackStatus.RESOLVED
        assert update.resolution_notes == "Fixed in version 1.2.0"


# =============================================================================
# Integration Tests (Require Database)
# =============================================================================


class TestFeedbackIntegration:
    """Integration tests that require database setup."""

    @pytest.mark.skip(reason="Requires database connection")
    def test_create_and_retrieve_feedback(self):
        """Test creating and retrieving feedback end-to-end."""
        pass

    @pytest.mark.skip(reason="Requires database connection")
    def test_admin_can_see_all_org_feedback(self):
        """Test that admins can see all feedback from their organization."""
        pass

    @pytest.mark.skip(reason="Requires database connection")
    def test_member_can_only_see_own_feedback(self):
        """Test that members can only see their own feedback."""
        pass

    @pytest.mark.skip(reason="Requires database connection")
    def test_stats_calculation(self):
        """Test feedback statistics are calculated correctly."""
        pass
