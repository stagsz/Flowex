from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.routes.drawings import BulkVerifyRequest, BulkVerifyResponse
from app.main import app
from app.services.drawings import (
    MAX_FILE_SIZE,
    FileValidationError,
    validate_file,
)

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
