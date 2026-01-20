"""Microsoft Graph API service for OneDrive and SharePoint."""

import urllib.parse
from datetime import datetime

import httpx

from app.core.config import settings
from app.services.cloud.base import (
    BrowseResult,
    CloudFile,
    CloudFolder,
    CloudStorageProvider,
    OAuthTokens,
    UserInfo,
)

# Microsoft Graph API scopes
MICROSOFT_SCOPES = [
    "openid",
    "profile",
    "email",
    "offline_access",
    "Files.ReadWrite.All",
    "Sites.ReadWrite.All",
]


class MicrosoftGraphProvider(CloudStorageProvider):
    """Microsoft Graph API provider for OneDrive and SharePoint."""

    GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"

    def __init__(self, site_id: str | None = None, drive_id: str | None = None):
        """Initialize with optional SharePoint site/drive IDs."""
        self.site_id = site_id
        self.drive_id = drive_id

    def _get_drive_path(self) -> str:
        """Get the correct drive path based on configuration."""
        if self.site_id and self.drive_id:
            return f"/sites/{self.site_id}/drives/{self.drive_id}"
        elif self.drive_id:
            return f"/drives/{self.drive_id}"
        else:
            return "/me/drive"

    def get_auth_url(self, state: str) -> str:
        """Get Microsoft OAuth authorization URL."""
        params = {
            "client_id": settings.MICROSOFT_CLIENT_ID,
            "response_type": "code",
            "redirect_uri": settings.MICROSOFT_REDIRECT_URI,
            "scope": " ".join(MICROSOFT_SCOPES),
            "state": state,
            "response_mode": "query",
            "prompt": "consent",
        }
        return f"{settings.microsoft_auth_url}?{urllib.parse.urlencode(params)}"

    async def exchange_code(self, code: str) -> OAuthTokens:
        """Exchange authorization code for tokens."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                settings.microsoft_token_url,
                data={
                    "client_id": settings.MICROSOFT_CLIENT_ID,
                    "client_secret": settings.MICROSOFT_CLIENT_SECRET,
                    "code": code,
                    "redirect_uri": settings.MICROSOFT_REDIRECT_URI,
                    "grant_type": "authorization_code",
                },
            )
            response.raise_for_status()
            data = response.json()

            return OAuthTokens(
                access_token=data["access_token"],
                refresh_token=data.get("refresh_token", ""),
                expires_in=data["expires_in"],
                token_type=data.get("token_type", "Bearer"),
                scope=data.get("scope", ""),
            )

    async def refresh_token(self, refresh_token: str) -> OAuthTokens:
        """Refresh an expired access token."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                settings.microsoft_token_url,
                data={
                    "client_id": settings.MICROSOFT_CLIENT_ID,
                    "client_secret": settings.MICROSOFT_CLIENT_SECRET,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                    "scope": " ".join(MICROSOFT_SCOPES),
                },
            )
            response.raise_for_status()
            data = response.json()

            return OAuthTokens(
                access_token=data["access_token"],
                refresh_token=data.get("refresh_token", refresh_token),
                expires_in=data["expires_in"],
                token_type=data.get("token_type", "Bearer"),
                scope=data.get("scope", ""),
            )

    async def get_user_info(self, access_token: str) -> UserInfo:
        """Get user information using access token."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.GRAPH_BASE_URL}/me",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            data = response.json()

            return UserInfo(
                email=data.get("mail") or data.get("userPrincipalName", ""),
                name=data.get("displayName"),
            )

    async def browse(
        self,
        access_token: str,
        folder_id: str | None = None,
    ) -> BrowseResult:
        """Browse folder contents."""
        drive_path = self._get_drive_path()

        if folder_id:
            endpoint = f"{self.GRAPH_BASE_URL}{drive_path}/items/{folder_id}/children"
            folder_endpoint = f"{self.GRAPH_BASE_URL}{drive_path}/items/{folder_id}"
        else:
            endpoint = f"{self.GRAPH_BASE_URL}{drive_path}/root/children"
            folder_endpoint = f"{self.GRAPH_BASE_URL}{drive_path}/root"

        async with httpx.AsyncClient() as client:
            # Get current folder info
            current_folder = None
            folder_response = await client.get(
                folder_endpoint,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if folder_response.status_code == 200:
                folder_data = folder_response.json()
                current_folder = CloudFolder(
                    id=folder_data["id"],
                    name=folder_data["name"],
                    path=folder_data.get("parentReference", {}).get("path", ""),
                    child_count=folder_data.get("folder", {}).get("childCount", 0),
                )

            # Get children
            response = await client.get(
                endpoint,
                headers={"Authorization": f"Bearer {access_token}"},
                params={"$top": 100},
            )
            response.raise_for_status()
            data = response.json()

            folders = []
            files = []

            for item in data.get("value", []):
                if "folder" in item:
                    folders.append(
                        CloudFolder(
                            id=item["id"],
                            name=item["name"],
                            path=item.get("parentReference", {}).get("path", ""),
                            child_count=item["folder"].get("childCount", 0),
                        )
                    )
                elif "file" in item:
                    files.append(
                        CloudFile(
                            id=item["id"],
                            name=item["name"],
                            path=item.get("parentReference", {}).get("path", ""),
                            size=item.get("size", 0),
                            mime_type=item.get("file", {}).get("mimeType", ""),
                            modified_at=datetime.fromisoformat(
                                item["lastModifiedDateTime"].replace("Z", "+00:00")
                            ),
                            thumbnail_url=item.get("thumbnails", [{}])[0].get(
                                "small", {}
                            ).get("url"),
                        )
                    )

            return BrowseResult(
                current_folder=current_folder,
                folders=folders,
                files=files,
            )

    async def search(
        self,
        access_token: str,
        query: str,
        file_type: str | None = None,
    ) -> list[CloudFile]:
        """Search for files."""
        drive_path = self._get_drive_path()
        endpoint = f"{self.GRAPH_BASE_URL}{drive_path}/root/search(q='{query}')"

        async with httpx.AsyncClient() as client:
            response = await client.get(
                endpoint,
                headers={"Authorization": f"Bearer {access_token}"},
                params={"$top": 50},
            )
            response.raise_for_status()
            data = response.json()

            files = []
            for item in data.get("value", []):
                # Skip folders
                if "folder" in item:
                    continue

                # Filter by file type if specified
                if file_type:
                    mime_type = item.get("file", {}).get("mimeType", "")
                    if file_type == "pdf" and mime_type != "application/pdf":
                        continue

                files.append(
                    CloudFile(
                        id=item["id"],
                        name=item["name"],
                        path=item.get("parentReference", {}).get("path", ""),
                        size=item.get("size", 0),
                        mime_type=item.get("file", {}).get("mimeType", ""),
                        modified_at=datetime.fromisoformat(
                            item["lastModifiedDateTime"].replace("Z", "+00:00")
                        ),
                    )
                )

            return files

    async def download_file(self, access_token: str, file_id: str) -> bytes:
        """Download file content."""
        drive_path = self._get_drive_path()
        endpoint = f"{self.GRAPH_BASE_URL}{drive_path}/items/{file_id}/content"

        async with httpx.AsyncClient() as client:
            response = await client.get(
                endpoint,
                headers={"Authorization": f"Bearer {access_token}"},
                follow_redirects=True,
            )
            response.raise_for_status()
            return response.content

    async def upload_file(
        self,
        access_token: str,
        folder_id: str,
        filename: str,
        content: bytes,
        mime_type: str = "application/octet-stream",
    ) -> CloudFile:
        """Upload file to folder."""
        drive_path = self._get_drive_path()

        # Use simple upload for files < 4MB, otherwise use upload session
        if len(content) < 4 * 1024 * 1024:
            endpoint = (
                f"{self.GRAPH_BASE_URL}{drive_path}/items/{folder_id}:/{filename}:/content"
            )
            async with httpx.AsyncClient() as client:
                response = await client.put(
                    endpoint,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": mime_type,
                    },
                    content=content,
                )
                response.raise_for_status()
                data = response.json()
        else:
            data = await self._upload_large_file(
                access_token, folder_id, filename, content, mime_type
            )

        return CloudFile(
            id=data["id"],
            name=data["name"],
            path=data.get("parentReference", {}).get("path", ""),
            size=data.get("size", 0),
            mime_type=data.get("file", {}).get("mimeType", mime_type),
            modified_at=datetime.fromisoformat(
                data["lastModifiedDateTime"].replace("Z", "+00:00")
            ),
        )

    async def _upload_large_file(
        self,
        access_token: str,
        folder_id: str,
        filename: str,
        content: bytes,
        mime_type: str,
    ) -> dict[str, object]:
        """Upload large file using upload session."""
        drive_path = self._get_drive_path()
        create_session_url = (
            f"{self.GRAPH_BASE_URL}{drive_path}/items/{folder_id}:/{filename}:/createUploadSession"
        )

        async with httpx.AsyncClient() as client:
            # Create upload session
            session_response = await client.post(
                create_session_url,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json={
                    "item": {
                        "@microsoft.graph.conflictBehavior": "rename",
                        "name": filename,
                    }
                },
            )
            session_response.raise_for_status()
            upload_url = session_response.json()["uploadUrl"]

            # Upload in chunks (10MB chunks)
            chunk_size = 10 * 1024 * 1024
            total_size = len(content)

            for start in range(0, total_size, chunk_size):
                end = min(start + chunk_size, total_size)
                chunk = content[start:end]

                response = await client.put(
                    upload_url,
                    headers={
                        "Content-Range": f"bytes {start}-{end - 1}/{total_size}",
                        "Content-Type": mime_type,
                    },
                    content=chunk,
                )
                response.raise_for_status()

                # Last chunk returns the completed item
                if end == total_size:
                    result: dict[str, object] = response.json()
                    return result

        raise RuntimeError("Upload failed to return completed item")

    async def create_folder(
        self,
        access_token: str,
        parent_id: str,
        name: str,
    ) -> CloudFolder:
        """Create a new folder."""
        drive_path = self._get_drive_path()
        endpoint = f"{self.GRAPH_BASE_URL}{drive_path}/items/{parent_id}/children"

        async with httpx.AsyncClient() as client:
            response = await client.post(
                endpoint,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json={
                    "name": name,
                    "folder": {},
                    "@microsoft.graph.conflictBehavior": "fail",
                },
            )
            response.raise_for_status()
            data = response.json()

            return CloudFolder(
                id=data["id"],
                name=data["name"],
                path=data.get("parentReference", {}).get("path", ""),
                child_count=0,
            )

    async def file_exists(
        self,
        access_token: str,
        folder_id: str,
        filename: str,
    ) -> bool:
        """Check if a file exists in folder."""
        drive_path = self._get_drive_path()
        endpoint = f"{self.GRAPH_BASE_URL}{drive_path}/items/{folder_id}:/{filename}"

        async with httpx.AsyncClient() as client:
            response = await client.get(
                endpoint,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            return response.status_code == 200

    async def get_sharepoint_sites(self, access_token: str) -> list[dict[str, str]]:
        """Get available SharePoint sites for the user."""
        endpoint = f"{self.GRAPH_BASE_URL}/sites?search=*"

        async with httpx.AsyncClient() as client:
            response = await client.get(
                endpoint,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            data = response.json()

            sites = []
            for site in data.get("value", []):
                sites.append(
                    {
                        "id": site["id"],
                        "name": site.get("displayName", site.get("name", "")),
                        "url": site.get("webUrl", ""),
                    }
                )
            return sites

    async def get_site_drives(self, access_token: str, site_id: str) -> list[dict[str, str]]:
        """Get drives (document libraries) in a SharePoint site."""
        endpoint = f"{self.GRAPH_BASE_URL}/sites/{site_id}/drives"

        async with httpx.AsyncClient() as client:
            response = await client.get(
                endpoint,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            data = response.json()

            drives = []
            for drive in data.get("value", []):
                drives.append(
                    {
                        "id": drive["id"],
                        "name": drive.get("name", ""),
                        "description": drive.get("description", ""),
                        "type": drive.get("driveType", ""),
                    }
                )
            return drives
