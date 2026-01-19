"""Base classes and interfaces for cloud storage providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass
class CloudFile:
    """Represents a file in cloud storage."""

    id: str
    name: str
    path: str
    size: int
    mime_type: str
    modified_at: datetime
    thumbnail_url: str | None = None


@dataclass
class CloudFolder:
    """Represents a folder in cloud storage."""

    id: str
    name: str
    path: str
    child_count: int = 0


@dataclass
class BrowseResult:
    """Result of browsing a cloud folder."""

    current_folder: CloudFolder | None
    folders: list[CloudFolder]
    files: list[CloudFile]


@dataclass
class OAuthTokens:
    """OAuth tokens from authorization."""

    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str = "Bearer"
    scope: str = ""


@dataclass
class UserInfo:
    """User info from OAuth provider."""

    email: str
    name: str | None = None


class CloudStorageProvider(ABC):
    """Abstract base class for cloud storage providers."""

    @abstractmethod
    def get_auth_url(self, state: str) -> str:
        """Get OAuth authorization URL."""
        pass

    @abstractmethod
    async def exchange_code(self, code: str) -> OAuthTokens:
        """Exchange authorization code for tokens."""
        pass

    @abstractmethod
    async def refresh_token(self, refresh_token: str) -> OAuthTokens:
        """Refresh an expired access token."""
        pass

    @abstractmethod
    async def get_user_info(self, access_token: str) -> UserInfo:
        """Get user information using access token."""
        pass

    @abstractmethod
    async def browse(
        self,
        access_token: str,
        folder_id: str | None = None,
    ) -> BrowseResult:
        """Browse folder contents."""
        pass

    @abstractmethod
    async def search(
        self,
        access_token: str,
        query: str,
        file_type: str | None = None,
    ) -> list[CloudFile]:
        """Search for files."""
        pass

    @abstractmethod
    async def download_file(self, access_token: str, file_id: str) -> bytes:
        """Download file content."""
        pass

    @abstractmethod
    async def upload_file(
        self,
        access_token: str,
        folder_id: str,
        filename: str,
        content: bytes,
        mime_type: str = "application/octet-stream",
    ) -> CloudFile:
        """Upload file to folder."""
        pass

    @abstractmethod
    async def create_folder(
        self,
        access_token: str,
        parent_id: str,
        name: str,
    ) -> CloudFolder:
        """Create a new folder."""
        pass

    @abstractmethod
    async def file_exists(
        self,
        access_token: str,
        folder_id: str,
        filename: str,
    ) -> bool:
        """Check if a file exists in folder."""
        pass
