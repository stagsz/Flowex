"""Tests for GDPR user endpoints (data export, account deletion) and activity logs."""

from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.deps import get_current_user, get_db
from app.main import app
from app.models import (
    CloudConnection,
    CloudProvider,
    Drawing,
    DrawingStatus,
    Line,
    Organization,
    Project,
    SSOProvider,
    Symbol,
    SymbolCategory,
    TextAnnotation,
    User,
    UserRole,
)
from app.models.audit_log import AuditAction, AuditLog, EntityType

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Reset rate limiter storage before each test."""
    limiter = app.state.limiter
    if hasattr(limiter, "_storage") and limiter._storage:
        try:
            limiter._storage.reset()
        except (AttributeError, Exception):
            pass
    yield


class TestGDPRDataExportAuth:
    """Test GDPR data export endpoint authentication."""

    def test_data_export_requires_auth(self):
        """Test data export endpoint requires authentication."""
        response = client.get("/api/v1/users/me/data-export")
        assert response.status_code == 403

    def test_data_export_invalid_token(self):
        """Test data export with invalid token returns 401."""
        response = client.get(
            "/api/v1/users/me/data-export",
            headers={"Authorization": "Bearer invalid_token"},
        )
        assert response.status_code == 401


class TestGDPRDataExportSuccess:
    """Test GDPR data export endpoint with mocked authentication."""

    def _create_mock_user(self, org: Organization) -> User:
        """Create a mock user for testing."""
        user = MagicMock(spec=User)
        user.id = uuid4()
        user.email = "test@example.com"
        user.name = "Test User"
        user.role = UserRole.MEMBER
        user.sso_provider = SSOProvider.GOOGLE
        user.sso_subject_id = "google-123"
        user.is_active = True
        user.organization_id = org.id
        user.organization = org
        user.created_at = datetime(2024, 1, 1, tzinfo=UTC)
        user.updated_at = datetime(2024, 1, 15, tzinfo=UTC)
        return user

    def _create_mock_org(self) -> Organization:
        """Create a mock organization for testing."""
        org = MagicMock(spec=Organization)
        org.id = uuid4()
        org.name = "Test Company"
        org.slug = "test-company"
        org.subscription_tier = MagicMock()
        org.subscription_tier.value = "professional"
        org.created_at = datetime(2024, 1, 1, tzinfo=UTC)
        org.updated_at = datetime(2024, 1, 1, tzinfo=UTC)
        return org

    def _create_mock_project(self, org_id: UUID) -> Project:
        """Create a mock project for testing."""
        project = MagicMock(spec=Project)
        project.id = uuid4()
        project.organization_id = org_id
        project.name = "Test Project"
        project.description = "A test project"
        project.is_archived = False
        project.created_at = datetime(2024, 1, 5, tzinfo=UTC)
        project.updated_at = datetime(2024, 1, 10, tzinfo=UTC)
        return project

    def _create_mock_drawing(self, project_id: UUID) -> Drawing:
        """Create a mock drawing for testing."""
        drawing = MagicMock(spec=Drawing)
        drawing.id = uuid4()
        drawing.project_id = project_id
        drawing.original_filename = "test_pid.pdf"
        drawing.storage_path = "organizations/123/2024/01/05/test.pdf"
        drawing.file_size_bytes = 1024000
        drawing.file_type = MagicMock()
        drawing.file_type.value = "pdf_vector"
        drawing.status = DrawingStatus.complete
        drawing.status.value = "complete"
        drawing.error_message = None
        drawing.processing_started_at = datetime(2024, 1, 5, 10, 0, tzinfo=UTC)
        drawing.processing_completed_at = datetime(2024, 1, 5, 10, 5, tzinfo=UTC)
        drawing.created_at = datetime(2024, 1, 5, tzinfo=UTC)
        drawing.updated_at = datetime(2024, 1, 5, tzinfo=UTC)
        return drawing

    def _create_mock_symbol(self, drawing_id: UUID) -> Symbol:
        """Create a mock symbol for testing."""
        symbol = MagicMock(spec=Symbol)
        symbol.id = uuid4()
        symbol.drawing_id = drawing_id
        symbol.symbol_class = "centrifugal_pump"
        symbol.category = SymbolCategory.EQUIPMENT
        symbol.category.value = "equipment"
        symbol.tag_number = "P-101"
        symbol.bbox_x = 100.0
        symbol.bbox_y = 200.0
        symbol.bbox_width = 50.0
        symbol.bbox_height = 50.0
        symbol.confidence = 0.95
        symbol.is_verified = True
        symbol.is_flagged = False
        symbol.is_deleted = False
        symbol.created_at = datetime(2024, 1, 5, tzinfo=UTC)
        return symbol

    def _create_mock_line(self, drawing_id: UUID) -> Line:
        """Create a mock line for testing."""
        line = MagicMock(spec=Line)
        line.id = uuid4()
        line.drawing_id = drawing_id
        line.line_number = "6-P-101"
        line.start_x = 0.0
        line.start_y = 0.0
        line.end_x = 100.0
        line.end_y = 100.0
        line.line_spec = "6\"-P-101-A1"
        line.pipe_class = "A1"
        line.insulation = "None"
        line.confidence = 0.90
        line.is_verified = False
        line.is_deleted = False
        line.created_at = datetime(2024, 1, 5, tzinfo=UTC)
        return line

    def _create_mock_text(self, drawing_id: UUID, symbol_id: UUID | None = None) -> TextAnnotation:
        """Create a mock text annotation for testing."""
        text = MagicMock(spec=TextAnnotation)
        text.id = uuid4()
        text.drawing_id = drawing_id
        text.text_content = "P-101"
        text.bbox_x = 150.0
        text.bbox_y = 200.0
        text.bbox_width = 30.0
        text.bbox_height = 15.0
        text.rotation = 0
        text.confidence = 0.98
        text.is_verified = True
        text.is_deleted = False
        text.associated_symbol_id = symbol_id
        text.created_at = datetime(2024, 1, 5, tzinfo=UTC)
        return text

    def _create_mock_cloud_connection(self, user_id: UUID, org_id: UUID) -> CloudConnection:
        """Create a mock cloud connection for testing."""
        conn = MagicMock(spec=CloudConnection)
        conn.id = uuid4()
        conn.user_id = user_id
        conn.organization_id = org_id
        conn.provider = CloudProvider.GOOGLE_DRIVE
        conn.provider.value = "google_drive"
        conn.account_email = "user@gmail.com"
        conn.account_name = "My Drive"
        conn.site_name = None
        conn.last_used_at = datetime(2024, 1, 10, tzinfo=UTC)
        conn.created_at = datetime(2024, 1, 5, tzinfo=UTC)
        return conn

    def test_data_export_auth_bypass_returns_response(self):
        """Test data export with auth bypass triggers the endpoint logic.

        This test verifies that the endpoint is accessible and returns
        the expected response when auth and database are mocked.
        """
        org = self._create_mock_org()
        user = self._create_mock_user(org)

        # Create mock DB session
        mock_db = MagicMock()

        # Mock organization query
        mock_db.query.return_value.filter.return_value.first.return_value = org

        # Mock projects query (empty list)
        mock_db.query.return_value.filter.return_value.all.return_value = []

        # Mock count queries (for symbols, lines, text annotations)
        mock_db.query.return_value.join.return_value.join.return_value.filter.return_value.count.return_value = 0

        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_db] = lambda: mock_db

        try:
            response = client.get("/api/v1/users/me/data-export")
            # With auth and DB mocked, we should get a 200 response
            assert response.status_code == 200
            data = response.json()
            assert data["user"]["email"] == "test@example.com"
            assert data["gdpr_article"] == "Article 15 - Right of Access"
        finally:
            app.dependency_overrides.clear()


class TestGDPRDataExportResponseStructure:
    """Test GDPR data export response structure validation."""

    def test_response_model_user_profile(self):
        """Test UserProfileExport model structure."""
        from app.api.routes.users import UserProfileExport

        profile = UserProfileExport(
            id="test-id",
            email="test@example.com",
            name="Test User",
            role="member",
            sso_provider="google",
            is_active=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        assert profile.id == "test-id"
        assert profile.email == "test@example.com"
        assert profile.sso_provider == "google"

    def test_response_model_organization(self):
        """Test OrganizationExport model structure."""
        from app.api.routes.users import OrganizationExport

        org = OrganizationExport(
            id="org-id",
            name="Test Org",
            slug="test-org",
            subscription_tier="professional",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        assert org.id == "org-id"
        assert org.subscription_tier == "professional"

    def test_response_model_symbol(self):
        """Test SymbolExport model structure."""
        from app.api.routes.users import SymbolExport

        symbol = SymbolExport(
            id="symbol-id",
            symbol_class="centrifugal_pump",
            category="equipment",
            tag_number="P-101",
            bbox_x=100.0,
            bbox_y=200.0,
            bbox_width=50.0,
            bbox_height=50.0,
            confidence=0.95,
            is_verified=True,
            is_flagged=False,
            created_at=datetime.now(UTC),
        )
        assert symbol.symbol_class == "centrifugal_pump"
        assert symbol.confidence == 0.95

    def test_response_model_line(self):
        """Test LineExport model structure."""
        from app.api.routes.users import LineExport

        line = LineExport(
            id="line-id",
            line_number="6-P-101",
            start_x=0.0,
            start_y=0.0,
            end_x=100.0,
            end_y=100.0,
            line_spec="6\"-P-101-A1",
            pipe_class="A1",
            insulation=None,
            confidence=0.90,
            is_verified=False,
            created_at=datetime.now(UTC),
        )
        assert line.line_number == "6-P-101"
        assert line.insulation is None

    def test_response_model_text_annotation(self):
        """Test TextAnnotationExport model structure."""
        from app.api.routes.users import TextAnnotationExport

        text = TextAnnotationExport(
            id="text-id",
            text_content="P-101",
            bbox_x=150.0,
            bbox_y=200.0,
            bbox_width=30.0,
            bbox_height=15.0,
            rotation=0,
            confidence=0.98,
            is_verified=True,
            associated_symbol_id="symbol-id",
            created_at=datetime.now(UTC),
        )
        assert text.text_content == "P-101"
        assert text.rotation == 0

    def test_response_model_drawing(self):
        """Test DrawingExport model structure."""
        from app.api.routes.users import DrawingExport, SymbolExport

        drawing = DrawingExport(
            id="drawing-id",
            original_filename="test.pdf",
            file_size_bytes=1024000,
            file_type="pdf_vector",
            status="complete",
            error_message=None,
            processing_started_at=datetime.now(UTC),
            processing_completed_at=datetime.now(UTC),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            symbols=[
                SymbolExport(
                    id="s1",
                    symbol_class="pump",
                    category="equipment",
                    tag_number="P-1",
                    bbox_x=0,
                    bbox_y=0,
                    bbox_width=10,
                    bbox_height=10,
                    confidence=0.9,
                    is_verified=True,
                    is_flagged=False,
                    created_at=datetime.now(UTC),
                )
            ],
            lines=[],
            text_annotations=[],
        )
        assert drawing.original_filename == "test.pdf"
        assert len(drawing.symbols) == 1

    def test_response_model_project(self):
        """Test ProjectExport model structure."""
        from app.api.routes.users import ProjectExport

        project = ProjectExport(
            id="project-id",
            name="Test Project",
            description="A test project",
            is_archived=False,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            drawings=[],
        )
        assert project.name == "Test Project"
        assert project.drawings == []

    def test_response_model_cloud_connection(self):
        """Test CloudConnectionExport model structure."""
        from app.api.routes.users import CloudConnectionExport

        conn = CloudConnectionExport(
            id="conn-id",
            provider="google_drive",
            account_email="user@gmail.com",
            account_name="My Drive",
            site_name=None,
            last_used_at=datetime.now(UTC),
            created_at=datetime.now(UTC),
        )
        assert conn.provider == "google_drive"
        assert conn.site_name is None

    def test_response_model_full_export(self):
        """Test full GDPRDataExportResponse model structure."""
        from app.api.routes.users import (
            GDPRDataExportResponse,
            OrganizationExport,
            UserProfileExport,
        )

        now = datetime.now(UTC)
        export = GDPRDataExportResponse(
            export_date=now,
            user=UserProfileExport(
                id="user-id",
                email="test@example.com",
                name="Test",
                role="member",
                sso_provider="google",
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            organization=OrganizationExport(
                id="org-id",
                name="Test Org",
                slug="test-org",
                subscription_tier="free_trial",
                created_at=now,
                updated_at=now,
            ),
            projects=[],
            cloud_connections=[],
            metadata={
                "total_projects": 0,
                "total_drawings": 0,
                "total_symbols": 0,
            },
        )
        assert export.gdpr_article == "Article 15 - Right of Access"
        assert export.export_format == "JSON"


class TestAccountDeletionAuth:
    """Test account deletion endpoint authentication."""

    def test_account_deletion_requires_auth(self):
        """Test account deletion endpoint requires authentication."""
        response = client.delete("/api/v1/users/me")
        assert response.status_code == 403

    def test_account_deletion_invalid_token(self):
        """Test account deletion with invalid token returns 401."""
        response = client.delete(
            "/api/v1/users/me",
            headers={"Authorization": "Bearer invalid_token"},
        )
        assert response.status_code == 401


class TestAccountDeletionResponseStructure:
    """Test account deletion response structure validation."""

    def test_response_model_account_deletion(self):
        """Test AccountDeletionResponse model structure."""
        from app.api.routes.users import AccountDeletionResponse

        response = AccountDeletionResponse(
            message="Account deletion scheduled",
            deletion_scheduled_at=datetime.now(UTC),
            grace_period_days=30,
            data_to_be_deleted=[
                "User profile",
                "Cloud connections",
            ],
        )
        assert response.grace_period_days == 30
        assert len(response.data_to_be_deleted) == 2


class TestGDPREndpointMetadata:
    """Test GDPR endpoint metadata and documentation."""

    def test_data_export_endpoint_exists(self):
        """Test data export endpoint is registered."""
        # Check that the endpoint exists in the OpenAPI schema
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert "/api/v1/users/me/data-export" in schema["paths"]

    def test_account_deletion_endpoint_exists(self):
        """Test account deletion endpoint is registered."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert "/api/v1/users/me" in schema["paths"]
        assert "delete" in schema["paths"]["/api/v1/users/me"]

    def test_users_tag_in_openapi(self):
        """Test users tag is present in OpenAPI schema."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        # Check paths for users tag instead of checking tags list
        data_export_path = schema["paths"].get("/api/v1/users/me/data-export", {})
        get_op = data_export_path.get("get", {})
        assert "users" in get_op.get("tags", [])


class TestUserActivityAuth:
    """Test user activity endpoint authentication."""

    def test_user_activity_requires_auth(self):
        """Test user activity endpoint requires authentication."""
        response = client.get("/api/v1/users/me/activity")
        assert response.status_code == 403

    def test_user_activity_invalid_token(self):
        """Test user activity with invalid token returns 401."""
        response = client.get(
            "/api/v1/users/me/activity",
            headers={"Authorization": "Bearer invalid_token"},
        )
        assert response.status_code == 401


class TestUserActivitySuccess:
    """Test user activity endpoint with mocked authentication."""

    def _create_mock_user(self) -> User:
        """Create a mock user for testing."""
        user = MagicMock(spec=User)
        user.id = uuid4()
        user.email = "test@example.com"
        user.name = "Test User"
        user.role = UserRole.MEMBER
        user.organization_id = uuid4()
        return user

    def _create_mock_audit_log(self, user_id, action: AuditAction) -> AuditLog:
        """Create a mock audit log entry."""
        log = MagicMock(spec=AuditLog)
        log.id = uuid4()
        log.user_id = user_id
        log.action = action
        log.entity_type = EntityType.DRAWING
        log.entity_id = uuid4()
        log.ip_address = "127.0.0.1"
        log.extra_data = {"filename": "test.pdf"}
        log.timestamp = datetime.now(UTC)
        return log

    def test_user_activity_returns_list(self):
        """Test user activity endpoint returns paginated list."""
        user = self._create_mock_user()
        mock_log = self._create_mock_audit_log(user.id, AuditAction.DRAWING_UPLOAD)

        # Create mock DB session
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.all.return_value = [mock_log]

        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_db] = lambda: mock_db

        try:
            response = client.get("/api/v1/users/me/activity")
            assert response.status_code == 200
            data = response.json()
            assert "items" in data
            assert "total" in data
            assert "page" in data
            assert "page_size" in data
            assert data["total"] == 1
            assert len(data["items"]) == 1
            assert data["items"][0]["action"] == "drawing_upload"
        finally:
            app.dependency_overrides.clear()

    def test_user_activity_pagination(self):
        """Test user activity endpoint pagination parameters."""
        user = self._create_mock_user()

        # Create mock DB session
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.count.return_value = 0
        mock_query.all.return_value = []

        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_db] = lambda: mock_db

        try:
            response = client.get("/api/v1/users/me/activity?page=2&page_size=10")
            assert response.status_code == 200
            data = response.json()
            assert data["page"] == 2
            assert data["page_size"] == 10
        finally:
            app.dependency_overrides.clear()

    def test_user_activity_filter_by_action(self):
        """Test user activity endpoint action filter."""
        user = self._create_mock_user()
        mock_log = self._create_mock_audit_log(user.id, AuditAction.LOGIN)

        # Create mock DB session
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.all.return_value = [mock_log]

        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_db] = lambda: mock_db

        try:
            response = client.get("/api/v1/users/me/activity?action=login")
            assert response.status_code == 200
            data = response.json()
            assert len(data["items"]) == 1
            assert data["items"][0]["action"] == "login"
        finally:
            app.dependency_overrides.clear()


class TestUserActivityResponseStructure:
    """Test user activity response structure validation."""

    def test_response_model_activity_item(self):
        """Test UserActivityItem model structure."""
        from app.api.routes.users import UserActivityItem

        item = UserActivityItem(
            id="test-id",
            action="drawing_upload",
            entity_type="drawing",
            entity_id="entity-123",
            ip_address="127.0.0.1",
            metadata={"filename": "test.pdf"},
            timestamp=datetime.now(UTC),
        )
        assert item.id == "test-id"
        assert item.action == "drawing_upload"
        assert item.metadata["filename"] == "test.pdf"

    def test_response_model_activity_list(self):
        """Test UserActivityListResponse model structure."""
        from app.api.routes.users import UserActivityItem, UserActivityListResponse

        response = UserActivityListResponse(
            items=[
                UserActivityItem(
                    id="item-1",
                    action="login",
                    entity_type=None,
                    entity_id=None,
                    ip_address="192.168.1.1",
                    metadata=None,
                    timestamp=datetime.now(UTC),
                )
            ],
            total=1,
            page=1,
            page_size=25,
        )
        assert response.total == 1
        assert response.page == 1
        assert len(response.items) == 1

    def test_activity_endpoint_exists_in_openapi(self):
        """Test user activity endpoint is registered in OpenAPI."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert "/api/v1/users/me/activity" in schema["paths"]
        assert "get" in schema["paths"]["/api/v1/users/me/activity"]
