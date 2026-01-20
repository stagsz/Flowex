"""Cloud storage service with token management."""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cloud_connection import CloudConnection, CloudProvider
from app.services.cloud.base import (
    BrowseResult,
    CloudFile,
    CloudFolder,
    CloudStorageProvider,
)
from app.services.cloud.encryption import TokenEncryption
from app.services.cloud.google import GoogleDriveProvider
from app.services.cloud.microsoft import MicrosoftGraphProvider


class CloudStorageService:
    """Service for managing cloud storage connections and operations.

    Note: OAuth state management has been moved to app.core.oauth_state
    which uses Redis for distributed storage.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    def _get_provider(self, connection: CloudConnection) -> CloudStorageProvider:
        """Get the appropriate provider for a connection."""
        if connection.provider == CloudProvider.ONEDRIVE:
            return MicrosoftGraphProvider()
        elif connection.provider == CloudProvider.SHAREPOINT:
            return MicrosoftGraphProvider(
                site_id=connection.site_id,
                drive_id=connection.drive_id,
            )
        elif connection.provider == CloudProvider.GOOGLE_DRIVE:
            return GoogleDriveProvider()
        else:
            raise ValueError(f"Unsupported provider: {connection.provider}")

    def _get_provider_for_type(self, provider_type: str) -> CloudStorageProvider:
        """Get provider instance for initial auth."""
        if provider_type in ("onedrive", "sharepoint", "microsoft"):
            return MicrosoftGraphProvider()
        elif provider_type in ("google_drive", "google"):
            return GoogleDriveProvider()
        else:
            raise ValueError(f"Unsupported provider type: {provider_type}")

    def get_auth_url(self, provider_type: str, state: str) -> str:
        """Get OAuth authorization URL for a provider."""
        provider = self._get_provider_for_type(provider_type)
        return provider.get_auth_url(state)

    async def handle_oauth_callback(
        self,
        provider_type: str,
        code: str,
        user_id: uuid.UUID,
        org_id: uuid.UUID,
    ) -> CloudConnection:
        """Handle OAuth callback and create connection."""
        provider = self._get_provider_for_type(provider_type)

        # Exchange code for tokens
        tokens = await provider.exchange_code(code)

        # Get user info
        user_info = await provider.get_user_info(tokens.access_token)

        # Determine cloud provider enum
        if provider_type in ("onedrive", "microsoft"):
            cloud_provider = CloudProvider.ONEDRIVE
        elif provider_type == "sharepoint":
            cloud_provider = CloudProvider.SHAREPOINT
        else:
            cloud_provider = CloudProvider.GOOGLE_DRIVE

        # Create connection
        connection = CloudConnection(
            user_id=user_id,
            organization_id=org_id,
            provider=cloud_provider,
            account_email=user_info.email,
            account_name=user_info.name,
            access_token_encrypted=TokenEncryption.encrypt(tokens.access_token),
            refresh_token_encrypted=TokenEncryption.encrypt(tokens.refresh_token),
            token_expires_at=datetime.now(UTC)
            + timedelta(seconds=tokens.expires_in),
        )

        self.db.add(connection)
        await self.db.commit()
        await self.db.refresh(connection)

        return connection

    async def get_connection(
        self,
        connection_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> CloudConnection | None:
        """Get a connection by ID, verifying user access."""
        result = await self.db.execute(
            select(CloudConnection).where(
                CloudConnection.id == connection_id,
                CloudConnection.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_connections(
        self,
        user_id: uuid.UUID,
        org_id: uuid.UUID,
    ) -> list[CloudConnection]:
        """Get all connections for a user in an organization."""
        result = await self.db.execute(
            select(CloudConnection).where(
                CloudConnection.user_id == user_id,
                CloudConnection.organization_id == org_id,
            )
        )
        return list(result.scalars().all())

    async def delete_connection(
        self,
        connection_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        """Delete a connection."""
        connection = await self.get_connection(connection_id, user_id)
        if not connection:
            return False

        await self.db.delete(connection)
        await self.db.commit()
        return True

    async def _get_valid_access_token(self, connection: CloudConnection) -> str:
        """Get a valid access token, refreshing if needed."""
        # Check if token expires within 5 minutes
        if connection.token_expires_at < datetime.now(UTC) + timedelta(
            minutes=5
        ):
            await self._refresh_connection_token(connection)

        return TokenEncryption.decrypt(connection.access_token_encrypted)

    async def _refresh_connection_token(self, connection: CloudConnection) -> None:
        """Refresh the access token for a connection."""
        provider = self._get_provider(connection)
        refresh_token = TokenEncryption.decrypt(connection.refresh_token_encrypted)

        tokens = await provider.refresh_token(refresh_token)

        connection.access_token_encrypted = TokenEncryption.encrypt(tokens.access_token)
        if tokens.refresh_token != refresh_token:
            connection.refresh_token_encrypted = TokenEncryption.encrypt(
                tokens.refresh_token
            )
        connection.token_expires_at = datetime.now(UTC) + timedelta(
            seconds=tokens.expires_in
        )

        await self.db.commit()

    async def _update_last_used(self, connection: CloudConnection) -> None:
        """Update the last_used_at timestamp."""
        connection.last_used_at = datetime.now(UTC)
        await self.db.commit()

    async def browse(
        self,
        connection_id: uuid.UUID,
        user_id: uuid.UUID,
        folder_id: str | None = None,
    ) -> BrowseResult:
        """Browse folder contents."""
        connection = await self.get_connection(connection_id, user_id)
        if not connection:
            raise ValueError("Connection not found")

        provider = self._get_provider(connection)
        access_token = await self._get_valid_access_token(connection)

        result = await provider.browse(access_token, folder_id)
        await self._update_last_used(connection)

        return result

    async def search(
        self,
        connection_id: uuid.UUID,
        user_id: uuid.UUID,
        query: str,
        file_type: str | None = None,
    ) -> list[CloudFile]:
        """Search for files."""
        connection = await self.get_connection(connection_id, user_id)
        if not connection:
            raise ValueError("Connection not found")

        provider = self._get_provider(connection)
        access_token = await self._get_valid_access_token(connection)

        files = await provider.search(access_token, query, file_type)
        await self._update_last_used(connection)

        return files

    async def download_file(
        self,
        connection_id: uuid.UUID,
        user_id: uuid.UUID,
        file_id: str,
    ) -> bytes:
        """Download file content."""
        connection = await self.get_connection(connection_id, user_id)
        if not connection:
            raise ValueError("Connection not found")

        provider = self._get_provider(connection)
        access_token = await self._get_valid_access_token(connection)

        content = await provider.download_file(access_token, file_id)
        await self._update_last_used(connection)

        return content

    async def upload_file(
        self,
        connection_id: uuid.UUID,
        user_id: uuid.UUID,
        folder_id: str,
        filename: str,
        content: bytes,
        mime_type: str = "application/octet-stream",
    ) -> CloudFile:
        """Upload file to cloud storage."""
        connection = await self.get_connection(connection_id, user_id)
        if not connection:
            raise ValueError("Connection not found")

        provider = self._get_provider(connection)
        access_token = await self._get_valid_access_token(connection)

        file = await provider.upload_file(
            access_token, folder_id, filename, content, mime_type
        )
        await self._update_last_used(connection)

        return file

    async def create_folder(
        self,
        connection_id: uuid.UUID,
        user_id: uuid.UUID,
        parent_id: str,
        name: str,
    ) -> CloudFolder:
        """Create a new folder."""
        connection = await self.get_connection(connection_id, user_id)
        if not connection:
            raise ValueError("Connection not found")

        provider = self._get_provider(connection)
        access_token = await self._get_valid_access_token(connection)

        folder = await provider.create_folder(access_token, parent_id, name)
        await self._update_last_used(connection)

        return folder

    async def file_exists(
        self,
        connection_id: uuid.UUID,
        user_id: uuid.UUID,
        folder_id: str,
        filename: str,
    ) -> bool:
        """Check if file exists in folder."""
        connection = await self.get_connection(connection_id, user_id)
        if not connection:
            raise ValueError("Connection not found")

        provider = self._get_provider(connection)
        access_token = await self._get_valid_access_token(connection)

        return await provider.file_exists(access_token, folder_id, filename)

    async def get_sharepoint_sites(
        self,
        connection_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> list[dict[str, str]]:
        """Get SharePoint sites (Microsoft only)."""
        connection = await self.get_connection(connection_id, user_id)
        if not connection:
            raise ValueError("Connection not found")

        if connection.provider not in (CloudProvider.ONEDRIVE, CloudProvider.SHAREPOINT):
            raise ValueError("SharePoint sites only available for Microsoft connections")

        provider = MicrosoftGraphProvider()
        access_token = await self._get_valid_access_token(connection)

        return await provider.get_sharepoint_sites(access_token)

    async def get_site_drives(
        self,
        connection_id: uuid.UUID,
        user_id: uuid.UUID,
        site_id: str,
    ) -> list[dict[str, str]]:
        """Get drives in a SharePoint site."""
        connection = await self.get_connection(connection_id, user_id)
        if not connection:
            raise ValueError("Connection not found")

        if connection.provider not in (CloudProvider.ONEDRIVE, CloudProvider.SHAREPOINT):
            raise ValueError("SharePoint drives only available for Microsoft connections")

        provider = MicrosoftGraphProvider()
        access_token = await self._get_valid_access_token(connection)

        return await provider.get_site_drives(access_token, site_id)

    async def configure_sharepoint(
        self,
        connection_id: uuid.UUID,
        user_id: uuid.UUID,
        site_id: str,
        site_name: str,
        drive_id: str,
    ) -> CloudConnection:
        """Configure a connection for SharePoint."""
        connection = await self.get_connection(connection_id, user_id)
        if not connection:
            raise ValueError("Connection not found")

        connection.provider = CloudProvider.SHAREPOINT
        connection.site_id = site_id
        connection.site_name = site_name
        connection.drive_id = drive_id

        await self.db.commit()
        await self.db.refresh(connection)

        return connection
