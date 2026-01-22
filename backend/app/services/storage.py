"""
Storage service with support for multiple providers.

Supports:
- AWS S3 (production)
- Supabase Storage (development)
- Local filesystem (testing)

The provider is selected via STORAGE_PROVIDER environment variable.
"""

import uuid
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from pathlib import Path
from typing import BinaryIO

import boto3
from botocore.exceptions import ClientError

from app.core.config import StorageProvider, settings


class StorageError(Exception):
    """Exception raised for storage errors."""

    pass


class BaseStorageService(ABC):
    """Abstract base class for storage services."""

    @abstractmethod
    def generate_storage_path(self, organization_id: uuid.UUID, filename: str) -> str:
        """Generate a unique storage path for a file."""
        pass

    @abstractmethod
    async def upload_file(
        self,
        file: BinaryIO,
        storage_path: str,
        content_type: str = "application/pdf",
    ) -> str:
        """Upload a file and return the storage path."""
        pass

    @abstractmethod
    async def download_file(self, storage_path: str) -> bytes:
        """Download a file and return its contents."""
        pass

    @abstractmethod
    async def delete_file(self, storage_path: str) -> None:
        """Delete a file."""
        pass

    @abstractmethod
    async def get_presigned_url(self, storage_path: str, expires_in: int = 3600) -> str:
        """Generate a presigned URL for downloading a file."""
        pass

    @abstractmethod
    async def get_presigned_upload_url(
        self,
        storage_path: str,
        content_type: str = "application/pdf",
        expires_in: int = 3600,
    ) -> str:
        """Generate a presigned URL for uploading a file."""
        pass

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for storage."""
        return "".join(c for c in filename if c.isalnum() or c in ".-_")

    def _generate_base_path(self, organization_id: uuid.UUID, filename: str) -> str:
        """Generate a standard path structure."""
        timestamp = datetime.now(UTC).strftime("%Y/%m/%d")
        file_id = uuid.uuid4().hex[:12]
        safe_filename = self._sanitize_filename(filename)
        return f"organizations/{organization_id}/{timestamp}/{file_id}_{safe_filename}"


class S3StorageService(BaseStorageService):
    """Service for managing file storage in AWS S3."""

    def __init__(self) -> None:
        self.s3_client = boto3.client(
            "s3",
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID or None,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY or None,
        )
        self.bucket = settings.AWS_S3_BUCKET

    def generate_storage_path(self, organization_id: uuid.UUID, filename: str) -> str:
        """Generate a unique storage path for a file."""
        return self._generate_base_path(organization_id, filename)

    async def upload_file(
        self,
        file: BinaryIO,
        storage_path: str,
        content_type: str = "application/pdf",
    ) -> str:
        """Upload a file to S3 and return the storage path."""
        try:
            self.s3_client.upload_fileobj(
                file,
                self.bucket,
                storage_path,
                ExtraArgs={
                    "ContentType": content_type,
                    "ServerSideEncryption": "AES256",
                },
            )
            return storage_path
        except ClientError as e:
            raise StorageError(f"Failed to upload file: {e}") from e

    async def download_file(self, storage_path: str) -> bytes:
        """Download a file from S3."""
        try:
            response = self.s3_client.get_object(Bucket=self.bucket, Key=storage_path)
            content: bytes = response["Body"].read()
            return content
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                raise FileNotFoundError(f"File not found: {storage_path}") from e
            raise StorageError(f"Failed to download file: {e}") from e

    async def delete_file(self, storage_path: str) -> None:
        """Delete a file from S3."""
        try:
            self.s3_client.delete_object(Bucket=self.bucket, Key=storage_path)
        except ClientError as e:
            raise StorageError(f"Failed to delete file: {e}") from e

    async def get_presigned_url(self, storage_path: str, expires_in: int = 3600) -> str:
        """Generate a presigned URL for downloading a file."""
        try:
            url: str = self.s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": storage_path},
                ExpiresIn=expires_in,
            )
            return url
        except ClientError as e:
            raise StorageError(f"Failed to generate presigned URL: {e}") from e

    async def get_presigned_upload_url(
        self,
        storage_path: str,
        content_type: str = "application/pdf",
        expires_in: int = 3600,
    ) -> str:
        """Generate a presigned URL for uploading a file directly to S3."""
        try:
            url: str = self.s3_client.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": self.bucket,
                    "Key": storage_path,
                    "ContentType": content_type,
                },
                ExpiresIn=expires_in,
            )
            return url
        except ClientError as e:
            raise StorageError(f"Failed to generate presigned upload URL: {e}") from e


class SupabaseStorageService(BaseStorageService):
    """Service for managing file storage in Supabase Storage."""

    def __init__(self) -> None:
        from supabase import Client, create_client

        if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
            raise StorageError(
                "Supabase configuration missing. Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY"
            )

        # Create client without proxy to avoid httpx version conflicts
        try:
            self.client = create_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_SERVICE_ROLE_KEY,
            )
        except TypeError:
            # Fallback for older/newer versions with different signatures
            self.client = Client(
                settings.SUPABASE_URL,
                settings.SUPABASE_SERVICE_ROLE_KEY,
            )
        self.bucket = settings.SUPABASE_STORAGE_BUCKET
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self) -> None:
        """Ensure the storage bucket exists."""
        try:
            # List buckets to check if ours exists
            buckets = self.client.storage.list_buckets()
            bucket_names = [b.name for b in buckets]

            if self.bucket not in bucket_names:
                # Create the bucket if it doesn't exist
                self.client.storage.create_bucket(
                    self.bucket,
                    options={
                        "public": False,
                        "file_size_limit": 52428800,  # 50MB
                        "allowed_mime_types": ["application/pdf", "image/png", "image/jpeg"],
                    },
                )
        except Exception:
            # Bucket might already exist or we don't have permission to create
            pass

    def generate_storage_path(self, organization_id: uuid.UUID, filename: str) -> str:
        """Generate a unique storage path for a file."""
        return self._generate_base_path(organization_id, filename)

    async def upload_file(
        self,
        file: BinaryIO,
        storage_path: str,
        content_type: str = "application/pdf",
    ) -> str:
        """Upload a file to Supabase Storage."""
        try:
            # Read file content
            file_content = file.read()

            # Upload to Supabase Storage with upsert to handle duplicates
            self.client.storage.from_(self.bucket).upload(
                path=storage_path,
                file=file_content,
                file_options={"content-type": content_type, "upsert": "true"},
            )

            return storage_path
        except Exception as e:
            raise StorageError(f"Failed to upload file to Supabase: {e}") from e

    async def download_file(self, storage_path: str) -> bytes:
        """Download a file from Supabase Storage."""
        try:
            response: bytes = self.client.storage.from_(self.bucket).download(storage_path)
            return response
        except Exception as e:
            if "not found" in str(e).lower():
                raise FileNotFoundError(f"File not found: {storage_path}") from e
            raise StorageError(f"Failed to download file from Supabase: {e}") from e

    async def delete_file(self, storage_path: str) -> None:
        """Delete a file from Supabase Storage."""
        try:
            self.client.storage.from_(self.bucket).remove([storage_path])
        except Exception as e:
            raise StorageError(f"Failed to delete file from Supabase: {e}") from e

    async def get_presigned_url(self, storage_path: str, expires_in: int = 3600) -> str:
        """Generate a signed URL for downloading a file."""
        try:
            result = self.client.storage.from_(self.bucket).create_signed_url(
                path=storage_path,
                expires_in=expires_in,
            )
            return str(result["signedUrl"])
        except Exception as e:
            raise StorageError(f"Failed to generate signed URL: {e}") from e

    async def get_presigned_upload_url(
        self,
        storage_path: str,
        content_type: str = "application/pdf",
        expires_in: int = 3600,
    ) -> str:
        """Generate a signed URL for uploading a file."""
        try:
            result = self.client.storage.from_(self.bucket).create_signed_upload_url(
                path=storage_path,
            )
            return str(result["signedUrl"])
        except Exception as e:
            raise StorageError(f"Failed to generate signed upload URL: {e}") from e


class LocalStorageService(BaseStorageService):
    """Service for local file storage (for testing)."""

    def __init__(self, base_dir: str | None = None):
        self.base_dir = Path(base_dir or "/tmp/flowex_storage")
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def generate_storage_path(self, organization_id: uuid.UUID, filename: str) -> str:
        """Generate a unique storage path for a file."""
        return self._generate_base_path(organization_id, filename)

    async def upload_file(
        self,
        file: BinaryIO,
        storage_path: str,
        content_type: str = "application/pdf",
    ) -> str:
        """Upload a file to local storage."""
        try:
            full_path = self.base_dir / storage_path
            full_path.parent.mkdir(parents=True, exist_ok=True)

            with open(full_path, "wb") as f:
                f.write(file.read())

            return storage_path
        except Exception as e:
            raise StorageError(f"Failed to upload file locally: {e}") from e

    async def download_file(self, storage_path: str) -> bytes:
        """Download a file from local storage."""
        try:
            full_path = self.base_dir / storage_path
            if not full_path.exists():
                raise FileNotFoundError(f"File not found: {storage_path}")

            with open(full_path, "rb") as f:
                return f.read()
        except FileNotFoundError:
            raise
        except Exception as e:
            raise StorageError(f"Failed to download file locally: {e}") from e

    async def delete_file(self, storage_path: str) -> None:
        """Delete a file from local storage."""
        try:
            full_path = self.base_dir / storage_path
            if full_path.exists():
                full_path.unlink()
        except Exception as e:
            raise StorageError(f"Failed to delete file locally: {e}") from e

    async def get_presigned_url(self, storage_path: str, expires_in: int = 3600) -> str:
        """Return a file:// URL for local files."""
        full_path = self.base_dir / storage_path
        return f"file://{full_path}"

    async def get_presigned_upload_url(
        self,
        storage_path: str,
        content_type: str = "application/pdf",
        expires_in: int = 3600,
    ) -> str:
        """Return a file:// URL for local upload."""
        full_path = self.base_dir / storage_path
        return f"file://{full_path}"


# Storage service factory and singleton

_storage_service: BaseStorageService | None = None


def get_storage_service() -> BaseStorageService:
    """
    Get the storage service based on configuration.

    Returns the appropriate storage service based on STORAGE_PROVIDER setting:
    - "supabase": SupabaseStorageService (default for development)
    - "aws": S3StorageService (for production)
    - "local": LocalStorageService (for testing)
    """
    global _storage_service

    if _storage_service is None:
        provider = settings.STORAGE_PROVIDER

        if provider == StorageProvider.SUPABASE:
            _storage_service = SupabaseStorageService()
        elif provider == StorageProvider.AWS:
            _storage_service = S3StorageService()
        elif provider == StorageProvider.LOCAL:
            _storage_service = LocalStorageService()
        else:
            raise StorageError(f"Unknown storage provider: {provider}")

    return _storage_service


def reset_storage_service() -> None:
    """Reset the storage service singleton (useful for testing)."""
    global _storage_service
    _storage_service = None
