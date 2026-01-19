import pytest

from app.services.drawings import (
    ALLOWED_CONTENT_TYPES,
    ALLOWED_EXTENSIONS,
    MAX_FILE_SIZE,
    FileValidationError,
    validate_file,
)


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
