from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.routes.drawings import (
    BulkLineVerifyRequest,
    BulkLineVerifyResponse,
    BulkVerifyRequest,
    BulkVerifyResponse,
    LineCreateRequest,
    LineResponse,
    LinesResponse,
    LineUpdateRequest,
    TitleBlockResponse,
    _extract_title_block_from_texts,
)
from app.main import app
from app.services.drawings import MAX_FILE_SIZE, FileValidationError, validate_file

client = TestClient(app)


class TestFileValidation:
    """Tests for file validation."""

    def test_valid_pdf_file(self):
        """Test validation passes for valid PDF file."""
        validate_file("document.pdf", "application/pdf", 1024)

    def test_invalid_extension(self):
        """Test validation fails for invalid file extension."""
        with pytest.raises(FileValidationError) as exc:
            validate_file("document.docx", "application/pdf", 1024)
        assert "Invalid file type" in str(exc.value)

    def test_invalid_content_type(self):
        """Test validation fails for invalid content type."""
        with pytest.raises(FileValidationError) as exc:
            validate_file("document.pdf", "application/msword", 1024)
        assert "Invalid content type" in str(exc.value)

    def test_file_too_large(self):
        """Test validation fails for file exceeding size limit."""
        with pytest.raises(FileValidationError) as exc:
            validate_file("document.pdf", "application/pdf", MAX_FILE_SIZE + 1)
        assert "File too large" in str(exc.value)

    def test_file_at_max_size(self):
        """Test validation passes for file at exactly max size."""
        validate_file("document.pdf", "application/pdf", MAX_FILE_SIZE)

    def test_file_no_extension(self):
        """Test validation fails for file without extension."""
        with pytest.raises(FileValidationError) as exc:
            validate_file("document", "application/pdf", 1024)
        assert "Invalid file type" in str(exc.value)

    def test_uppercase_extension(self):
        """Test validation passes for uppercase extension."""
        validate_file("document.PDF", "application/pdf", 1024)


class TestStoragePathGeneration:
    """Tests for storage path generation."""

    def test_path_contains_organization_id(self):
        """Test generated path contains organization ID."""
        from uuid import uuid4

        from app.services.storage import S3StorageService

        service = S3StorageService()
        org_id = uuid4()
        path = service.generate_storage_path(org_id, "test.pdf")
        assert str(org_id) in path

    def test_path_sanitizes_filename(self):
        """Test generated path sanitizes special characters."""
        from uuid import uuid4

        from app.services.storage import S3StorageService

        service = S3StorageService()
        org_id = uuid4()
        path = service.generate_storage_path(org_id, "test file (1).pdf")
        assert "(" not in path
        assert ")" not in path
        assert " " not in path

    def test_path_has_date_structure(self):
        """Test generated path includes date-based directory structure."""
        from uuid import uuid4

        from app.services.storage import S3StorageService

        service = S3StorageService()
        org_id = uuid4()
        path = service.generate_storage_path(org_id, "test.pdf")
        # Path should have format: organizations/{org_id}/YYYY/MM/DD/{file_id}_{filename}
        parts = path.split("/")
        assert parts[0] == "organizations"
        assert len(parts) >= 5  # organizations, org_id, year, month, day, filename


class TestBulkVerifyRequest:
    """Tests for BulkVerifyRequest model."""

    def test_valid_request_single_id(self):
        """Test valid request with single symbol ID."""
        request = BulkVerifyRequest(symbol_ids=["abc-123"])
        assert request.symbol_ids == ["abc-123"]

    def test_valid_request_multiple_ids(self):
        """Test valid request with multiple symbol IDs."""
        ids = [str(uuid4()) for _ in range(5)]
        request = BulkVerifyRequest(symbol_ids=ids)
        assert len(request.symbol_ids) == 5

    def test_empty_list_allowed(self):
        """Test that empty list is technically valid (will return 0 verified)."""
        request = BulkVerifyRequest(symbol_ids=[])
        assert request.symbol_ids == []


class TestBulkVerifyResponse:
    """Tests for BulkVerifyResponse model."""

    def test_response_structure(self):
        """Test response has correct structure."""
        response = BulkVerifyResponse(
            verified_count=3,
            verified_ids=["a", "b", "c"],
            failed_ids=["d"],
        )
        assert response.verified_count == 3
        assert len(response.verified_ids) == 3
        assert len(response.failed_ids) == 1

    def test_response_all_verified(self):
        """Test response when all symbols are verified."""
        ids = ["a", "b", "c"]
        response = BulkVerifyResponse(
            verified_count=3,
            verified_ids=ids,
            failed_ids=[],
        )
        assert response.failed_ids == []


class TestBulkVerifyEndpoint:
    """Tests for bulk verify endpoint authentication and access control."""

    def test_bulk_verify_requires_auth(self):
        """Test bulk verify endpoint requires authentication."""
        drawing_id = str(uuid4())
        response = client.post(
            f"/api/v1/drawings/{drawing_id}/symbols/bulk-verify",
            json={"symbol_ids": [str(uuid4())]},
        )
        # Should return 403 (Forbidden) without auth
        assert response.status_code == 403

    def test_bulk_verify_invalid_drawing_id_requires_auth(self):
        """Test bulk verify with invalid drawing ID requires auth first."""
        response = client.post(
            "/api/v1/drawings/invalid-uuid/symbols/bulk-verify",
            json={"symbol_ids": [str(uuid4())]},
        )
        # Auth check happens before validation, so returns 403
        assert response.status_code == 403

    def test_bulk_verify_missing_body_requires_auth(self):
        """Test bulk verify with missing request body requires auth first."""
        drawing_id = str(uuid4())
        response = client.post(
            f"/api/v1/drawings/{drawing_id}/symbols/bulk-verify",
        )
        # Auth check happens before body validation, so returns 403
        assert response.status_code == 403

    def test_bulk_verify_empty_symbol_ids(self):
        """Test bulk verify with empty symbol_ids array requires auth."""
        drawing_id = str(uuid4())
        response = client.post(
            f"/api/v1/drawings/{drawing_id}/symbols/bulk-verify",
            json={"symbol_ids": []},
        )
        # Should return 403 (Forbidden) without auth
        assert response.status_code == 403


class TestTitleBlockExtraction:
    """Tests for title block extraction functionality."""

    def _make_mock_text(
        self,
        content: str,
        bbox_x: float = 600.0,
        bbox_y: float = 500.0,
        bbox_width: float = 50.0,
        bbox_height: float = 12.0,
        is_deleted: bool = False,
    ) -> MagicMock:
        """Create a mock TextAnnotation object."""
        mock = MagicMock()
        mock.text_content = content
        mock.bbox_x = bbox_x
        mock.bbox_y = bbox_y
        mock.bbox_width = bbox_width
        mock.bbox_height = bbox_height
        mock.is_deleted = is_deleted
        return mock

    def test_extract_drawing_number(self):
        """Test extraction of drawing number from text."""
        texts = [
            self._make_mock_text("DWG-12345", 700, 500),
            self._make_mock_text("Some other text", 100, 100),
        ]
        result = _extract_title_block_from_texts(texts)
        assert result.drawing_number == "12345"

    def test_extract_drawing_number_pid_format(self):
        """Test extraction of P&ID drawing number format."""
        texts = [self._make_mock_text("P&ID-001", 700, 500)]
        result = _extract_title_block_from_texts(texts)
        assert result.drawing_number == "001"

    def test_extract_revision(self):
        """Test extraction of revision from text."""
        texts = [self._make_mock_text("REV A", 700, 500)]
        result = _extract_title_block_from_texts(texts)
        assert result.revision == "A"

    def test_extract_revision_variation(self):
        """Test extraction of revision with different format."""
        texts = [self._make_mock_text("REVISION: 2", 700, 500)]
        result = _extract_title_block_from_texts(texts)
        assert result.revision == "2"

    def test_extract_scale(self):
        """Test extraction of scale from text."""
        texts = [self._make_mock_text("SCALE: 1:50", 700, 500)]
        result = _extract_title_block_from_texts(texts)
        assert result.scale is not None
        assert "1" in result.scale and "50" in result.scale

    def test_extract_scale_simple(self):
        """Test extraction of simple scale format."""
        texts = [self._make_mock_text("1:100", 700, 500)]
        result = _extract_title_block_from_texts(texts)
        assert result.scale == "1:100"

    def test_extract_date_slash_format(self):
        """Test extraction of date with slash format."""
        texts = [self._make_mock_text("15/12/2025", 700, 500)]
        result = _extract_title_block_from_texts(texts)
        assert result.date == "15/12/2025"

    def test_extract_date_dash_format(self):
        """Test extraction of date with ISO dash format (YYYY-MM-DD)."""
        texts = [self._make_mock_text("2025-12-15", 700, 500)]
        result = _extract_title_block_from_texts(texts)
        assert result.date == "2025-12-15"

    def test_extract_date_short_year(self):
        """Test extraction of date with short year format."""
        texts = [self._make_mock_text("15-12-25", 700, 500)]
        result = _extract_title_block_from_texts(texts)
        assert result.date == "15-12-25"

    def test_extract_sheet(self):
        """Test extraction of sheet number."""
        texts = [self._make_mock_text("SHEET 1 OF 5", 700, 500)]
        result = _extract_title_block_from_texts(texts)
        assert result.sheet is not None
        assert "1" in result.sheet

    def test_extract_drawn_by(self):
        """Test extraction of drawn by field."""
        texts = [self._make_mock_text("DRAWN: JMS", 700, 500)]
        result = _extract_title_block_from_texts(texts)
        assert result.drawn_by == "JMS"

    def test_extract_checked_by(self):
        """Test extraction of checked by field."""
        texts = [self._make_mock_text("CHECKED: KLR", 700, 500)]
        result = _extract_title_block_from_texts(texts)
        assert result.checked_by == "KLR"

    def test_extract_approved_by(self):
        """Test extraction of approved by field."""
        texts = [self._make_mock_text("APPROVED: ABC", 700, 500)]
        result = _extract_title_block_from_texts(texts)
        assert result.approved_by == "ABC"

    def test_extract_project_name(self):
        """Test extraction of project name."""
        texts = [self._make_mock_text("PROJECT: WtE Plant Alpha", 700, 500)]
        result = _extract_title_block_from_texts(texts)
        assert result.project_name is not None
        assert "WtE" in result.project_name or "Alpha" in result.project_name

    def test_extract_title_longest_text(self):
        """Test that title is extracted as the longest non-keyword text."""
        texts = [
            self._make_mock_text("REV A", 700, 500),
            self._make_mock_text("Process Area 100 - Feed System Overview", 700, 510),
            self._make_mock_text("1:50", 700, 520),
        ]
        result = _extract_title_block_from_texts(texts)
        assert result.title == "Process Area 100 - Feed System Overview"

    def test_empty_texts_list(self):
        """Test extraction with empty texts list."""
        result = _extract_title_block_from_texts([])
        assert result.texts_analyzed == 0
        assert result.extraction_confidence == 0.0
        assert result.drawing_number is None

    def test_deleted_texts_excluded(self):
        """Test that deleted texts are excluded from analysis."""
        texts = [
            self._make_mock_text("DWG-12345", 700, 500, is_deleted=True),
            self._make_mock_text("No pattern here", 700, 510),
        ]
        result = _extract_title_block_from_texts(texts)
        # The deleted text with the drawing number should not be found
        assert result.drawing_number is None

    def test_texts_outside_title_block_region_fallback(self):
        """Test that texts outside title block region are still analyzed as fallback."""
        # Text at top-left (outside title block region)
        texts = [self._make_mock_text("DWG-99999", 50, 50)]
        result = _extract_title_block_from_texts(texts)
        # Should still find it via fallback
        assert result.drawing_number == "99999"

    def test_multiple_fields_extraction(self):
        """Test extraction of multiple fields from various texts."""
        texts = [
            self._make_mock_text("P&ID-001", 700, 500),
            self._make_mock_text("REV B", 700, 510),
            self._make_mock_text("SCALE: 1:50", 700, 520),
            self._make_mock_text("DRAWN: JMS", 700, 530),
            self._make_mock_text("15/01/2026", 700, 540),
        ]
        result = _extract_title_block_from_texts(texts)
        assert result.drawing_number == "001"
        assert result.revision == "B"
        assert result.scale is not None
        assert result.drawn_by == "JMS"
        assert result.date == "15/01/2026"
        assert result.extraction_confidence > 0

    def test_extraction_confidence_calculation(self):
        """Test that extraction confidence is calculated correctly."""
        # All fields found
        texts = [
            self._make_mock_text("DWG-001", 700, 500),
            self._make_mock_text("REV A", 700, 510),
            self._make_mock_text("1:50", 700, 520),
            self._make_mock_text("15/01/2026", 700, 530),
            self._make_mock_text("SHEET 1 OF 1", 700, 540),
            self._make_mock_text("DRAWN: JMS", 700, 550),
            self._make_mock_text("CHECKED: KLR", 700, 560),
            self._make_mock_text("APPROVED: ABC", 700, 570),
        ]
        result = _extract_title_block_from_texts(texts)
        assert result.extraction_confidence > 0.5

    def test_response_model_structure(self):
        """Test TitleBlockResponse model has correct structure."""
        response = TitleBlockResponse(
            drawing_number="DWG-001",
            revision="A",
            title="Test Title",
            project_name="Test Project",
            date="2026-01-15",
            scale="1:50",
            drawn_by="JMS",
            checked_by="KLR",
            approved_by="ABC",
            sheet="1 OF 1",
            extraction_confidence=0.8,
            texts_analyzed=10,
        )
        assert response.drawing_number == "DWG-001"
        assert response.revision == "A"
        assert response.extraction_confidence == 0.8


class TestTitleBlockEndpoint:
    """Tests for title block API endpoint authentication and access control."""

    def test_title_block_requires_auth(self):
        """Test title block endpoint requires authentication."""
        drawing_id = str(uuid4())
        response = client.get(f"/api/v1/drawings/{drawing_id}/title-block")
        # Should return 403 (Forbidden) without auth
        assert response.status_code == 403

    def test_title_block_invalid_drawing_id_requires_auth(self):
        """Test title block with invalid drawing ID requires auth first."""
        response = client.get("/api/v1/drawings/invalid-uuid/title-block")
        # Auth check happens before validation, so returns 403
        assert response.status_code == 403


# =============================================================================
# Line/Connection CRUD Tests (EDIT-05)
# =============================================================================


class TestLineResponseModel:
    """Tests for LineResponse model."""

    def test_line_response_structure(self):
        """Test LineResponse has correct structure."""
        response = LineResponse(
            id="test-id",
            line_number="L-001",
            start_x=100.0,
            start_y=200.0,
            end_x=300.0,
            end_y=400.0,
            line_spec="6\"-CS-A1A",
            pipe_class="A1A",
            insulation="INSUL",
            confidence=0.95,
            is_verified=True,
            is_deleted=False,
        )
        assert response.id == "test-id"
        assert response.line_number == "L-001"
        assert response.start_x == 100.0
        assert response.end_x == 300.0
        assert response.is_verified is True

    def test_line_response_optional_fields(self):
        """Test LineResponse with optional fields as None."""
        response = LineResponse(
            id="test-id",
            line_number=None,
            start_x=100.0,
            start_y=200.0,
            end_x=300.0,
            end_y=400.0,
            line_spec=None,
            pipe_class=None,
            insulation=None,
            confidence=None,
            is_verified=False,
            is_deleted=False,
        )
        assert response.line_number is None
        assert response.line_spec is None
        assert response.confidence is None


class TestLinesResponseModel:
    """Tests for LinesResponse model."""

    def test_lines_response_structure(self):
        """Test LinesResponse has correct structure."""
        response = LinesResponse(
            lines=[
                LineResponse(
                    id="1",
                    line_number="L-001",
                    start_x=0, start_y=0, end_x=100, end_y=100,
                    line_spec=None, pipe_class=None, insulation=None,
                    confidence=0.9, is_verified=True, is_deleted=False,
                ),
                LineResponse(
                    id="2",
                    line_number="L-002",
                    start_x=100, start_y=100, end_x=200, end_y=200,
                    line_spec=None, pipe_class=None, insulation=None,
                    confidence=0.8, is_verified=False, is_deleted=False,
                ),
            ],
            summary={
                "total_lines": 2,
                "verified_lines": 1,
                "pending_lines": 1,
                "low_confidence_lines": 0,
            },
        )
        assert len(response.lines) == 2
        assert response.summary["total_lines"] == 2
        assert response.summary["verified_lines"] == 1

    def test_lines_response_empty(self):
        """Test LinesResponse with empty lines list."""
        response = LinesResponse(
            lines=[],
            summary={
                "total_lines": 0,
                "verified_lines": 0,
                "pending_lines": 0,
                "low_confidence_lines": 0,
            },
        )
        assert len(response.lines) == 0
        assert response.summary["total_lines"] == 0


class TestLineCreateRequest:
    """Tests for LineCreateRequest model."""

    def test_line_create_request_full(self):
        """Test LineCreateRequest with all fields."""
        request = LineCreateRequest(
            line_number="L-001",
            start_x=100.0,
            start_y=200.0,
            end_x=300.0,
            end_y=400.0,
            line_spec="6\"-CS-A1A",
            pipe_class="A1A",
            insulation="INSUL",
            confidence=0.95,
            is_verified=True,
        )
        assert request.line_number == "L-001"
        assert request.start_x == 100.0
        assert request.is_verified is True

    def test_line_create_request_minimal(self):
        """Test LineCreateRequest with only required fields."""
        request = LineCreateRequest(
            start_x=100.0,
            start_y=200.0,
            end_x=300.0,
            end_y=400.0,
        )
        assert request.line_number is None
        assert request.line_spec is None
        assert request.is_verified is False


class TestLineUpdateRequest:
    """Tests for LineUpdateRequest model."""

    def test_line_update_request_all_fields(self):
        """Test LineUpdateRequest with all fields."""
        request = LineUpdateRequest(
            line_number="L-002",
            start_x=150.0,
            start_y=250.0,
            end_x=350.0,
            end_y=450.0,
            line_spec="8\"-CS-B1B",
            pipe_class="B1B",
            insulation="NONE",
            is_verified=True,
        )
        assert request.line_number == "L-002"
        assert request.start_x == 150.0
        assert request.is_verified is True

    def test_line_update_request_partial(self):
        """Test LineUpdateRequest with only some fields."""
        request = LineUpdateRequest(
            line_number="L-003",
            is_verified=True,
        )
        assert request.line_number == "L-003"
        assert request.start_x is None
        assert request.is_verified is True

    def test_line_update_request_empty(self):
        """Test LineUpdateRequest with no fields (all None)."""
        request = LineUpdateRequest()
        assert request.line_number is None
        assert request.start_x is None
        assert request.is_verified is None


class TestBulkLineVerifyRequest:
    """Tests for BulkLineVerifyRequest model."""

    def test_bulk_line_verify_request_single_id(self):
        """Test valid request with single line ID."""
        request = BulkLineVerifyRequest(line_ids=["line-123"])
        assert request.line_ids == ["line-123"]

    def test_bulk_line_verify_request_multiple_ids(self):
        """Test valid request with multiple line IDs."""
        ids = [str(uuid4()) for _ in range(5)]
        request = BulkLineVerifyRequest(line_ids=ids)
        assert len(request.line_ids) == 5

    def test_bulk_line_verify_request_empty(self):
        """Test that empty list is valid."""
        request = BulkLineVerifyRequest(line_ids=[])
        assert request.line_ids == []


class TestBulkLineVerifyResponse:
    """Tests for BulkLineVerifyResponse model."""

    def test_bulk_line_verify_response_structure(self):
        """Test response has correct structure."""
        response = BulkLineVerifyResponse(
            verified_count=3,
            verified_ids=["a", "b", "c"],
            failed_ids=["d"],
        )
        assert response.verified_count == 3
        assert len(response.verified_ids) == 3
        assert len(response.failed_ids) == 1

    def test_bulk_line_verify_response_all_verified(self):
        """Test response when all lines are verified."""
        ids = ["a", "b", "c"]
        response = BulkLineVerifyResponse(
            verified_count=3,
            verified_ids=ids,
            failed_ids=[],
        )
        assert response.failed_ids == []


class TestLinesEndpointAuth:
    """Tests for line endpoints authentication and access control."""

    def test_get_lines_requires_auth(self):
        """Test get lines endpoint requires authentication."""
        drawing_id = str(uuid4())
        response = client.get(f"/api/v1/drawings/{drawing_id}/lines")
        assert response.status_code == 403

    def test_create_line_requires_auth(self):
        """Test create line endpoint requires authentication."""
        drawing_id = str(uuid4())
        response = client.post(
            f"/api/v1/drawings/{drawing_id}/lines",
            json={
                "start_x": 100.0,
                "start_y": 200.0,
                "end_x": 300.0,
                "end_y": 400.0,
            },
        )
        assert response.status_code == 403

    def test_update_line_requires_auth(self):
        """Test update line endpoint requires authentication."""
        drawing_id = str(uuid4())
        line_id = str(uuid4())
        response = client.patch(
            f"/api/v1/drawings/{drawing_id}/lines/{line_id}",
            json={"line_number": "L-001"},
        )
        assert response.status_code == 403

    def test_delete_line_requires_auth(self):
        """Test delete line endpoint requires authentication."""
        drawing_id = str(uuid4())
        line_id = str(uuid4())
        response = client.delete(
            f"/api/v1/drawings/{drawing_id}/lines/{line_id}",
        )
        assert response.status_code == 403

    def test_verify_line_requires_auth(self):
        """Test verify line endpoint requires authentication."""
        drawing_id = str(uuid4())
        line_id = str(uuid4())
        response = client.post(
            f"/api/v1/drawings/{drawing_id}/lines/{line_id}/verify",
        )
        assert response.status_code == 403

    def test_unverify_line_requires_auth(self):
        """Test unverify line endpoint requires authentication."""
        drawing_id = str(uuid4())
        line_id = str(uuid4())
        response = client.post(
            f"/api/v1/drawings/{drawing_id}/lines/{line_id}/unverify",
        )
        assert response.status_code == 403

    def test_bulk_verify_lines_requires_auth(self):
        """Test bulk verify lines endpoint requires authentication."""
        drawing_id = str(uuid4())
        response = client.post(
            f"/api/v1/drawings/{drawing_id}/lines/bulk-verify",
            json={"line_ids": [str(uuid4())]},
        )
        assert response.status_code == 403

    def test_restore_line_requires_auth(self):
        """Test restore line endpoint requires authentication."""
        drawing_id = str(uuid4())
        line_id = str(uuid4())
        response = client.post(
            f"/api/v1/drawings/{drawing_id}/lines/{line_id}/restore",
        )
        assert response.status_code == 403

    def test_invalid_drawing_id_requires_auth(self):
        """Test that invalid drawing ID still requires auth first."""
        response = client.get("/api/v1/drawings/invalid-uuid/lines")
        assert response.status_code == 403

    def test_invalid_line_id_requires_auth(self):
        """Test that invalid line ID still requires auth first."""
        drawing_id = str(uuid4())
        response = client.patch(
            f"/api/v1/drawings/{drawing_id}/lines/invalid-uuid",
            json={"line_number": "L-001"},
        )
        assert response.status_code == 403
