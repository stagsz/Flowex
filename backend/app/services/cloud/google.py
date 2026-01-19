"""Google Drive API service."""

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

# Google OAuth scopes
GOOGLE_SCOPES = [
    "openid",
    "profile",
    "email",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive.readonly",
]


class GoogleDriveProvider(CloudStorageProvider):
    """Google Drive API provider."""

    DRIVE_BASE_URL = "https://www.googleapis.com/drive/v3"
    UPLOAD_URL = "https://www.googleapis.com/upload/drive/v3"
    USER_INFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

    def get_auth_url(self, state: str) -> str:
        """Get Google OAuth authorization URL."""
        params = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "response_type": "code",
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "scope": " ".join(GOOGLE_SCOPES),
            "state": state,
            "access_type": "offline",
            "prompt": "consent",
        }
        return f"{settings.google_auth_url}?{urllib.parse.urlencode(params)}"

    async def exchange_code(self, code: str) -> OAuthTokens:
        """Exchange authorization code for tokens."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                settings.google_token_url,
                data={
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "code": code,
                    "redirect_uri": settings.GOOGLE_REDIRECT_URI,
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
                settings.google_token_url,
                data={
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
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
                self.USER_INFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            data = response.json()

            return UserInfo(
                email=data.get("email", ""),
                name=data.get("name"),
            )

    async def browse(
        self,
        access_token: str,
        folder_id: str | None = None,
    ) -> BrowseResult:
        """Browse folder contents."""
        parent_id = folder_id or "root"
        query = f"'{parent_id}' in parents and trashed = false"

        async with httpx.AsyncClient() as client:
            # Get current folder info
            current_folder = None
            if folder_id:
                folder_response = await client.get(
                    f"{self.DRIVE_BASE_URL}/files/{folder_id}",
                    headers={"Authorization": f"Bearer {access_token}"},
                    params={"fields": "id,name,parents"},
                )
                if folder_response.status_code == 200:
                    folder_data = folder_response.json()
                    current_folder = CloudFolder(
                        id=folder_data["id"],
                        name=folder_data["name"],
                        path="",  # Google Drive doesn't expose full path easily
                        child_count=0,
                    )
            else:
                current_folder = CloudFolder(
                    id="root",
                    name="My Drive",
                    path="",
                    child_count=0,
                )

            # Get children
            response = await client.get(
                f"{self.DRIVE_BASE_URL}/files",
                headers={"Authorization": f"Bearer {access_token}"},
                params={
                    "q": query,
                    "fields": "files(id,name,mimeType,size,modifiedTime,parents,thumbnailLink)",
                    "pageSize": 100,
                    "orderBy": "folder,name",
                },
            )
            response.raise_for_status()
            data = response.json()

            folders = []
            files = []

            for item in data.get("files", []):
                if item["mimeType"] == "application/vnd.google-apps.folder":
                    folders.append(
                        CloudFolder(
                            id=item["id"],
                            name=item["name"],
                            path="",
                            child_count=0,
                        )
                    )
                else:
                    files.append(
                        CloudFile(
                            id=item["id"],
                            name=item["name"],
                            path="",
                            size=int(item.get("size", 0)),
                            mime_type=item["mimeType"],
                            modified_at=datetime.fromisoformat(
                                item["modifiedTime"].replace("Z", "+00:00")
                            ),
                            thumbnail_url=item.get("thumbnailLink"),
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
        search_query = f"name contains '{query}' and trashed = false"

        if file_type == "pdf":
            search_query += " and mimeType = 'application/pdf'"

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.DRIVE_BASE_URL}/files",
                headers={"Authorization": f"Bearer {access_token}"},
                params={
                    "q": search_query,
                    "fields": "files(id,name,mimeType,size,modifiedTime,parents)",
                    "pageSize": 50,
                },
            )
            response.raise_for_status()
            data = response.json()

            files = []
            for item in data.get("files", []):
                # Skip folders
                if item["mimeType"] == "application/vnd.google-apps.folder":
                    continue

                files.append(
                    CloudFile(
                        id=item["id"],
                        name=item["name"],
                        path="",
                        size=int(item.get("size", 0)),
                        mime_type=item["mimeType"],
                        modified_at=datetime.fromisoformat(
                            item["modifiedTime"].replace("Z", "+00:00")
                        ),
                    )
                )

            return files

    async def download_file(self, access_token: str, file_id: str) -> bytes:
        """Download file content."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.DRIVE_BASE_URL}/files/{file_id}",
                headers={"Authorization": f"Bearer {access_token}"},
                params={"alt": "media"},
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
        # Use simple upload for files < 5MB, otherwise use resumable upload
        if len(content) < 5 * 1024 * 1024:
            return await self._simple_upload(
                access_token, folder_id, filename, content, mime_type
            )
        else:
            return await self._resumable_upload(
                access_token, folder_id, filename, content, mime_type
            )

    async def _simple_upload(
        self,
        access_token: str,
        folder_id: str,
        filename: str,
        content: bytes,
        mime_type: str,
    ) -> CloudFile:
        """Simple upload for small files."""
        import json

        metadata = {
            "name": filename,
            "parents": [folder_id],
        }

        async with httpx.AsyncClient() as client:
            # Use multipart upload
            boundary = "flowex_upload_boundary"
            body = (
                f"--{boundary}\r\n"
                f'Content-Type: application/json; charset=UTF-8\r\n\r\n'
                f'{json.dumps(metadata)}\r\n'
                f"--{boundary}\r\n"
                f"Content-Type: {mime_type}\r\n\r\n"
            ).encode() + content + f"\r\n--{boundary}--".encode()

            response = await client.post(
                f"{self.UPLOAD_URL}/files",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": f"multipart/related; boundary={boundary}",
                },
                content=body,
                params={
                    "uploadType": "multipart",
                    "fields": "id,name,mimeType,size,modifiedTime",
                },
            )
            response.raise_for_status()
            data = response.json()

            return CloudFile(
                id=data["id"],
                name=data["name"],
                path="",
                size=int(data.get("size", 0)),
                mime_type=data.get("mimeType", mime_type),
                modified_at=datetime.fromisoformat(
                    data["modifiedTime"].replace("Z", "+00:00")
                ),
            )

    async def _resumable_upload(
        self,
        access_token: str,
        folder_id: str,
        filename: str,
        content: bytes,
        mime_type: str,
    ) -> CloudFile:
        """Resumable upload for large files."""

        metadata = {
            "name": filename,
            "parents": [folder_id],
        }

        async with httpx.AsyncClient() as client:
            # Initiate resumable upload
            init_response = await client.post(
                f"{self.UPLOAD_URL}/files",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                    "X-Upload-Content-Type": mime_type,
                    "X-Upload-Content-Length": str(len(content)),
                },
                params={"uploadType": "resumable"},
                json=metadata,
            )
            init_response.raise_for_status()
            upload_url = init_response.headers["Location"]

            # Upload in chunks (10MB)
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

                # 308 Resume Incomplete for intermediate chunks
                # 200/201 for final chunk
                if response.status_code in (200, 201):
                    data = response.json()
                    return CloudFile(
                        id=data["id"],
                        name=data["name"],
                        path="",
                        size=int(data.get("size", 0)),
                        mime_type=data.get("mimeType", mime_type),
                        modified_at=datetime.fromisoformat(
                            data["modifiedTime"].replace("Z", "+00:00")
                        ),
                    )
                elif response.status_code != 308:
                    response.raise_for_status()

        raise RuntimeError("Upload failed to return completed file")

    async def create_folder(
        self,
        access_token: str,
        parent_id: str,
        name: str,
    ) -> CloudFolder:
        """Create a new folder."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.DRIVE_BASE_URL}/files",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json={
                    "name": name,
                    "mimeType": "application/vnd.google-apps.folder",
                    "parents": [parent_id],
                },
            )
            response.raise_for_status()
            data = response.json()

            return CloudFolder(
                id=data["id"],
                name=data["name"],
                path="",
                child_count=0,
            )

    async def file_exists(
        self,
        access_token: str,
        folder_id: str,
        filename: str,
    ) -> bool:
        """Check if a file exists in folder."""
        query = (
            f"name = '{filename}' and '{folder_id}' in parents and trashed = false"
        )

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.DRIVE_BASE_URL}/files",
                headers={"Authorization": f"Bearer {access_token}"},
                params={
                    "q": query,
                    "fields": "files(id)",
                    "pageSize": 1,
                },
            )
            response.raise_for_status()
            data = response.json()

            return len(data.get("files", [])) > 0
