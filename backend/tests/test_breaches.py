"""Tests for security breach API endpoints (GDPR Article 33)."""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import User, UserRole
from app.models.security_breach import (
    BreachCategory,
    BreachSeverity,
    BreachStatus,
    SecurityBreach,
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
def mock_breach(mock_admin_user):
    """Create a mock breach record."""
    breach = MagicMock(spec=SecurityBreach)
    breach.id = uuid.uuid4()
    breach.organization_id = mock_admin_user.organization_id
    breach.reported_by_id = mock_admin_user.id
    breach.reported_by = mock_admin_user
    breach.title = "Unauthorized access detected"
    breach.description = "Suspicious login attempts from unknown IP addresses."
    breach.severity = BreachSeverity.HIGH
    breach.status = BreachStatus.DETECTED
    breach.category = BreachCategory.CONFIDENTIALITY
    breach.detected_at = datetime.now(UTC)
    breach.contained_at = None
    breach.resolved_at = None
    breach.affected_users_count = 50
    breach.data_categories_affected = ["email", "name"]
    breach.authority_notified = False
    breach.authority_notified_at = None
    breach.authority_reference = None
    breach.users_notified = False
    breach.users_notified_at = None
    breach.root_cause = None
    breach.remediation_steps = None
    breach.preventive_measures = None
    breach.created_at = datetime.now(UTC)
    breach.updated_at = datetime.now(UTC)
    return breach


# =============================================================================
# Model Tests
# =============================================================================


class TestBreachEnums:
    """Test breach enum values."""

    def test_breach_severity_values(self):
        """Test BreachSeverity enum has all expected values."""
        assert BreachSeverity.LOW.value == "low"
        assert BreachSeverity.MEDIUM.value == "medium"
        assert BreachSeverity.HIGH.value == "high"
        assert BreachSeverity.CRITICAL.value == "critical"

    def test_breach_status_values(self):
        """Test BreachStatus enum has all expected values."""
        assert BreachStatus.DETECTED.value == "detected"
        assert BreachStatus.INVESTIGATING.value == "investigating"
        assert BreachStatus.CONTAINED.value == "contained"
        assert BreachStatus.NOTIFYING.value == "notifying"
        assert BreachStatus.RESOLVED.value == "resolved"

    def test_breach_category_values(self):
        """Test BreachCategory enum has all expected values."""
        assert BreachCategory.CONFIDENTIALITY.value == "confidentiality"
        assert BreachCategory.INTEGRITY.value == "integrity"
        assert BreachCategory.AVAILABILITY.value == "availability"


# =============================================================================
# API Endpoint Tests (Unauthenticated)
# =============================================================================


class TestReportBreach:
    """Tests for POST /api/v1/breaches endpoint."""

    def test_report_breach_unauthenticated(self):
        """Test that unauthenticated requests are rejected."""
        response = client.post(
            "/api/v1/breaches",
            json={
                "title": "Test Breach",
                "description": "A test security breach for testing purposes.",
            },
        )
        assert response.status_code in (401, 403)

    def test_report_breach_payload_validation(self):
        """Test that invalid payloads are rejected."""
        # Missing required fields
        response = client.post(
            "/api/v1/breaches",
            json={},
        )
        assert response.status_code in (401, 403, 422)


class TestListBreaches:
    """Tests for GET /api/v1/breaches endpoint."""

    def test_list_breaches_unauthenticated(self):
        """Test that unauthenticated requests are rejected."""
        response = client.get("/api/v1/breaches")
        assert response.status_code in (401, 403)


class TestBreachStats:
    """Tests for GET /api/v1/breaches/stats endpoint."""

    def test_get_stats_unauthenticated(self):
        """Test that unauthenticated requests are rejected."""
        response = client.get("/api/v1/breaches/stats")
        assert response.status_code in (401, 403)


class TestGetBreach:
    """Tests for GET /api/v1/breaches/{id} endpoint."""

    def test_get_breach_unauthenticated(self):
        """Test that unauthenticated requests are rejected."""
        breach_id = uuid.uuid4()
        response = client.get(f"/api/v1/breaches/{breach_id}")
        assert response.status_code in (401, 403)


class TestUpdateBreach:
    """Tests for PATCH /api/v1/breaches/{id} endpoint."""

    def test_update_breach_unauthenticated(self):
        """Test that unauthenticated requests are rejected."""
        breach_id = uuid.uuid4()
        response = client.patch(
            f"/api/v1/breaches/{breach_id}",
            json={"status": "investigating"},
        )
        assert response.status_code in (401, 403)


class TestNotifyAuthority:
    """Tests for POST /api/v1/breaches/{id}/notify-authority endpoint."""

    def test_notify_authority_unauthenticated(self):
        """Test that unauthenticated requests are rejected."""
        breach_id = uuid.uuid4()
        response = client.post(
            f"/api/v1/breaches/{breach_id}/notify-authority",
            json={"authority_reference": "DPA-2026-001"},
        )
        assert response.status_code in (401, 403)


class TestNotifyUsers:
    """Tests for POST /api/v1/breaches/{id}/notify-users endpoint."""

    def test_notify_users_unauthenticated(self):
        """Test that unauthenticated requests are rejected."""
        breach_id = uuid.uuid4()
        response = client.post(
            f"/api/v1/breaches/{breach_id}/notify-users",
            json={"notification_method": "email"},
        )
        assert response.status_code in (401, 403)


class TestResolveBreach:
    """Tests for POST /api/v1/breaches/{id}/resolve endpoint."""

    def test_resolve_breach_unauthenticated(self):
        """Test that unauthenticated requests are rejected."""
        breach_id = uuid.uuid4()
        response = client.post(f"/api/v1/breaches/{breach_id}/resolve")
        assert response.status_code in (401, 403)


# =============================================================================
# Request/Response Model Tests
# =============================================================================


class TestBreachRequestModels:
    """Tests for breach request/response models."""

    def test_create_breach_model_valid(self):
        """Test CreateBreachRequest model with valid data."""
        from app.api.routes.breaches import CreateBreachRequest

        now = datetime.now(UTC)
        data = CreateBreachRequest(
            title="Unauthorized database access",
            description="Suspicious queries detected from external IP address.",
            severity=BreachSeverity.CRITICAL,
            category=BreachCategory.CONFIDENTIALITY,
            detected_at=now,
            affected_users_count=1000,
            data_categories_affected=["email", "name", "drawings"],
        )

        assert data.title == "Unauthorized database access"
        assert data.severity == BreachSeverity.CRITICAL
        assert data.category == BreachCategory.CONFIDENTIALITY
        assert data.affected_users_count == 1000
        assert len(data.data_categories_affected) == 3

    def test_create_breach_model_defaults(self):
        """Test CreateBreachRequest model default values."""
        from app.api.routes.breaches import CreateBreachRequest

        data = CreateBreachRequest(
            title="Simple breach report",
            description="A simple breach description for testing.",
        )

        assert data.severity == BreachSeverity.MEDIUM
        assert data.category == BreachCategory.CONFIDENTIALITY
        assert data.affected_users_count == 0
        assert data.data_categories_affected is None

    def test_create_breach_model_validation(self):
        """Test CreateBreachRequest model validation constraints."""
        from pydantic import ValidationError

        from app.api.routes.breaches import CreateBreachRequest

        # Title too short
        with pytest.raises(ValidationError):
            CreateBreachRequest(
                title="AB",  # Min 5 chars
                description="Valid description with enough characters.",
            )

        # Description too short
        with pytest.raises(ValidationError):
            CreateBreachRequest(
                title="Valid title here",
                description="Short",  # Min 20 chars
            )

        # Negative affected users count
        with pytest.raises(ValidationError):
            CreateBreachRequest(
                title="Valid title here",
                description="Valid description with enough characters.",
                affected_users_count=-1,
            )

    def test_update_breach_model(self):
        """Test UpdateBreachRequest model."""
        from app.api.routes.breaches import UpdateBreachRequest

        data = UpdateBreachRequest(
            status=BreachStatus.CONTAINED,
            root_cause="Compromised API credentials",
            remediation_steps="Rotated all API keys and revoked compromised tokens.",
            preventive_measures="Implemented key rotation policy and monitoring.",
        )

        assert data.status == BreachStatus.CONTAINED
        assert data.root_cause == "Compromised API credentials"
        assert "Rotated" in str(data.remediation_steps)

    def test_breach_response_model(self):
        """Test BreachResponse model."""
        from app.api.routes.breaches import BreachResponse

        now = datetime.now(UTC)
        deadline = now + timedelta(hours=72)

        data = BreachResponse(
            id=str(uuid.uuid4()),
            title="Test Breach",
            description="Test breach description for model testing.",
            severity="high",
            status="detected",
            category="confidentiality",
            detected_at=now,
            contained_at=None,
            resolved_at=None,
            affected_users_count=100,
            data_categories_affected=["email"],
            authority_notified=False,
            authority_notified_at=None,
            authority_reference=None,
            users_notified=False,
            users_notified_at=None,
            root_cause=None,
            remediation_steps=None,
            preventive_measures=None,
            reported_by_id=str(uuid.uuid4()),
            reported_by_name="Test Admin",
            hours_since_detection=1.5,
            notification_deadline=deadline,
            is_past_notification_deadline=False,
            created_at=now,
            updated_at=now,
        )

        assert data.severity == "high"
        assert data.status == "detected"
        assert data.affected_users_count == 100
        assert data.is_past_notification_deadline is False

    def test_breach_stats_model(self):
        """Test BreachStatsResponse model."""
        from app.api.routes.breaches import BreachStatsResponse

        stats = BreachStatsResponse(
            total_breaches=25,
            open_breaches=5,
            critical_breaches=2,
            breaches_pending_authority_notification=3,
            breaches_past_deadline=1,
            average_time_to_containment_hours=12.5,
            average_time_to_resolution_hours=48.0,
        )

        assert stats.total_breaches == 25
        assert stats.open_breaches == 5
        assert stats.critical_breaches == 2
        assert stats.breaches_past_deadline == 1
        assert stats.average_time_to_containment_hours == 12.5

    def test_notify_authority_request_model(self):
        """Test NotifyAuthorityRequest model."""
        from app.api.routes.breaches import NotifyAuthorityRequest

        data = NotifyAuthorityRequest(
            authority_reference="DPA-2026-00123",
            notes="Notification submitted via online portal.",
        )

        assert data.authority_reference == "DPA-2026-00123"
        assert "online portal" in str(data.notes)

    def test_notify_users_request_model(self):
        """Test NotifyUsersRequest model."""
        from app.api.routes.breaches import NotifyUsersRequest

        data = NotifyUsersRequest(
            notification_method="email",
            message_summary="Informed users of potential data exposure and recommended password change.",
        )

        assert data.notification_method == "email"
        assert "password change" in str(data.message_summary)


# =============================================================================
# Business Logic Tests
# =============================================================================


class TestBreachDeadlineCalculation:
    """Tests for 72-hour notification deadline calculation."""

    def test_deadline_not_passed(self):
        """Test deadline calculation when within 72 hours."""
        from app.api.routes.breaches import _serialize_breach

        now = datetime.now(UTC)
        breach = MagicMock(spec=SecurityBreach)
        breach.id = uuid.uuid4()
        breach.title = "Test Breach"
        breach.description = "Test description here."
        breach.severity = BreachSeverity.HIGH
        breach.status = BreachStatus.DETECTED
        breach.category = BreachCategory.CONFIDENTIALITY
        breach.detected_at = now - timedelta(hours=24)  # 24 hours ago
        breach.contained_at = None
        breach.resolved_at = None
        breach.affected_users_count = 10
        breach.data_categories_affected = None
        breach.authority_notified = False
        breach.authority_notified_at = None
        breach.authority_reference = None
        breach.users_notified = False
        breach.users_notified_at = None
        breach.root_cause = None
        breach.remediation_steps = None
        breach.preventive_measures = None
        breach.reported_by_id = None
        breach.reported_by = None
        breach.created_at = now
        breach.updated_at = now

        response = _serialize_breach(breach)

        assert response.hours_since_detection >= 24.0
        assert response.hours_since_detection < 25.0
        assert response.is_past_notification_deadline is False

    def test_deadline_passed(self):
        """Test deadline calculation when past 72 hours."""
        from app.api.routes.breaches import _serialize_breach

        now = datetime.now(UTC)
        breach = MagicMock(spec=SecurityBreach)
        breach.id = uuid.uuid4()
        breach.title = "Old Breach"
        breach.description = "Old breach description here."
        breach.severity = BreachSeverity.HIGH
        breach.status = BreachStatus.DETECTED
        breach.category = BreachCategory.CONFIDENTIALITY
        breach.detected_at = now - timedelta(hours=100)  # 100 hours ago
        breach.contained_at = None
        breach.resolved_at = None
        breach.affected_users_count = 10
        breach.data_categories_affected = None
        breach.authority_notified = False  # Not notified yet
        breach.authority_notified_at = None
        breach.authority_reference = None
        breach.users_notified = False
        breach.users_notified_at = None
        breach.root_cause = None
        breach.remediation_steps = None
        breach.preventive_measures = None
        breach.reported_by_id = None
        breach.reported_by = None
        breach.created_at = now
        breach.updated_at = now

        response = _serialize_breach(breach)

        assert response.hours_since_detection >= 100.0
        assert response.is_past_notification_deadline is True

    def test_deadline_not_applicable_when_notified(self):
        """Test deadline is not flagged when authority already notified."""
        from app.api.routes.breaches import _serialize_breach

        now = datetime.now(UTC)
        breach = MagicMock(spec=SecurityBreach)
        breach.id = uuid.uuid4()
        breach.title = "Notified Breach"
        breach.description = "Breach with authority notified."
        breach.severity = BreachSeverity.HIGH
        breach.status = BreachStatus.NOTIFYING
        breach.category = BreachCategory.CONFIDENTIALITY
        breach.detected_at = now - timedelta(hours=100)  # 100 hours ago
        breach.contained_at = None
        breach.resolved_at = None
        breach.affected_users_count = 10
        breach.data_categories_affected = None
        breach.authority_notified = True  # Already notified
        breach.authority_notified_at = now - timedelta(hours=50)
        breach.authority_reference = "DPA-2026-001"
        breach.users_notified = False
        breach.users_notified_at = None
        breach.root_cause = None
        breach.remediation_steps = None
        breach.preventive_measures = None
        breach.reported_by_id = None
        breach.reported_by = None
        breach.created_at = now
        breach.updated_at = now

        response = _serialize_breach(breach)

        # Even though 100 hours passed, authority was notified
        assert response.is_past_notification_deadline is False


# =============================================================================
# Integration Tests (Require Database)
# =============================================================================


class TestBreachIntegration:
    """Integration tests that require database setup."""

    @pytest.mark.skip(reason="Requires database connection")
    def test_create_and_retrieve_breach(self):
        """Test creating and retrieving a breach end-to-end."""
        pass

    @pytest.mark.skip(reason="Requires database connection")
    def test_breach_status_workflow(self):
        """Test breach status transitions: detected -> investigating -> contained -> resolved."""
        pass

    @pytest.mark.skip(reason="Requires database connection")
    def test_notification_workflow(self):
        """Test authority and user notification workflow."""
        pass

    @pytest.mark.skip(reason="Requires database connection")
    def test_stats_calculation(self):
        """Test breach statistics are calculated correctly."""
        pass

    @pytest.mark.skip(reason="Requires database connection")
    def test_member_cannot_access_breaches(self):
        """Test that non-admin members cannot access breach endpoints."""
        pass

    @pytest.mark.skip(reason="Requires database connection")
    def test_audit_logging(self):
        """Test that all breach operations are logged to audit trail."""
        pass
