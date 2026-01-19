import uuid
from datetime import datetime, timezone
from typing import BinaryIO

import boto3
from botocore.exceptions import ClientError

from app.core.config import settings


class S3StorageService:
    """Service for managing file storage in AWS S3."""

    def __init__(self):
        self.s3_client = boto3.client(
            "s3",
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID or None,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY or None,
        )
        self.bucket = settings.AWS_S3_BUCKET

    def generate_storage_path(self, organization_id: uuid.UUID, filename: str) -> str:
        """Generate a unique storage path for a file."""
        timestamp = datetime.now(timezone.utc).strftime("%Y/%m/%d")
        file_id = uuid.uuid4().hex[:12]
        # Sanitize filename
        safe_filename = "".join(c for c in filename if c.isalnum() or c in ".-_")
        return f"organizations/{organization_id}/{timestamp}/{file_id}_{safe_filename}"

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
            return response["Body"].read()
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
            url = self.s3_client.generate_presigned_url(
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
            url = self.s3_client.generate_presigned_url(
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


class StorageError(Exception):
    """Exception raised for storage errors."""

    pass


# Singleton instance
_storage_service: S3StorageService | None = None


def get_storage_service() -> S3StorageService:
    """Get or create the storage service instance."""
    global _storage_service
    if _storage_service is None:
        _storage_service = S3StorageService()
    return _storage_service
