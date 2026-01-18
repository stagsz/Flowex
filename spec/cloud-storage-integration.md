# Spec: Cloud Storage Integration

## Job to be Done
Allow users to import P&ID files from and export results to their existing cloud storage (OneDrive, SharePoint, Google Drive).

## Functional Requirements

### Supported Providers
| ID | Requirement | Priority |
|----|-------------|----------|
| CSI-01 | Microsoft OneDrive integration | Must-Have |
| CSI-02 | Microsoft SharePoint integration | Must-Have |
| CSI-03 | Google Drive integration | Must-Have |

### Import Features
| ID | Requirement | Priority |
|----|-------------|----------|
| IMP-01 | Browse cloud storage folders | Must-Have |
| IMP-02 | Select single file to import | Must-Have |
| IMP-03 | Select multiple files (batch import) | Must-Have |
| IMP-04 | Search files by name | Should-Have |
| IMP-05 | Filter by file type (PDF only) | Must-Have |
| IMP-06 | Show file metadata (size, modified date) | Must-Have |
| IMP-07 | Remember last accessed folder | Should-Have |

### Export Features
| ID | Requirement | Priority |
|----|-------------|----------|
| EXP-01 | Select export destination folder | Must-Have |
| EXP-02 | Create new folder in destination | Should-Have |
| EXP-03 | Export single file to cloud | Must-Have |
| EXP-04 | Export multiple files (batch export) | Must-Have |
| EXP-05 | Maintain folder structure option | Should-Have |
| EXP-06 | Overwrite confirmation for existing files | Must-Have |

### Connection Management
| ID | Requirement | Priority |
|----|-------------|----------|
| CON-01 | Connect account via OAuth | Must-Have |
| CON-02 | Disconnect account | Must-Have |
| CON-03 | View connected accounts | Must-Have |
| CON-04 | Multiple accounts per provider | Should-Have |
| CON-05 | Token refresh without re-auth | Must-Have |

## User Interface

### Connection Settings
```
┌─────────────────────────────────────────────────────────────────────────┐
│  SETTINGS > Integrations                                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  CLOUD STORAGE                                                           │
│  ─────────────────────────────────────────────────────────────────────  │
│                                                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  [Microsoft Logo]  Microsoft OneDrive                              │  │
│  │                                                                    │  │
│  │  ● Connected as: anna.muller@epcfirm.eu                           │  │
│  │    Connected: Jan 10, 2026                                         │  │
│  │                                                                    │  │
│  │  [Disconnect]                                                      │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  [Google Logo]  Google Drive                                       │  │
│  │                                                                    │  │
│  │  ○ Not connected                                                   │  │
│  │                                                                    │  │
│  │  [Connect Google Drive]                                            │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  [SharePoint Logo]  SharePoint                                     │  │
│  │                                                                    │  │
│  │  ○ Not connected                                                   │  │
│  │                                                                    │  │
│  │  [Connect SharePoint]                                              │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### File Picker (Import)
```
┌─────────────────────────────────────────────────────────────────────────┐
│  Import from OneDrive                                           [×]     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  📁 My Files > Engineering > P&IDs > WtE Project                        │
│  ─────────────────────────────────────────────────────────────────────  │
│                                                                          │
│  🔍 Search files...                          [PDF Only ✓]              │
│                                                                          │
│  ─────────────────────────────────────────────────────────────────────  │
│  □  Name                          Size        Modified                  │
│  ─────────────────────────────────────────────────────────────────────  │
│  □  📁 Archive                    —           Jan 5, 2026               │
│  ☑  📄 P&ID-001.pdf               2.3 MB      Jan 15, 2026              │
│  ☑  📄 P&ID-002.pdf               1.8 MB      Jan 15, 2026              │
│  □  📄 P&ID-003.pdf               3.1 MB      Jan 14, 2026              │
│  □  📄 README.txt                 4 KB        Jan 10, 2026              │
│  ─────────────────────────────────────────────────────────────────────  │
│                                                                          │
│  2 files selected (4.1 MB)                                              │
│                                                                          │
│  [Cancel]                                              [Import Selected] │
└─────────────────────────────────────────────────────────────────────────┘
```

### Folder Picker (Export)
```
┌─────────────────────────────────────────────────────────────────────────┐
│  Export to OneDrive                                             [×]     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Select destination folder:                                              │
│  ─────────────────────────────────────────────────────────────────────  │
│                                                                          │
│  📁 My Files > Engineering > P&IDs > WtE Project > Exports             │
│                                                                          │
│  ─────────────────────────────────────────────────────────────────────  │
│  Name                                          Modified                  │
│  ─────────────────────────────────────────────────────────────────────  │
│  📁 2024-Q4                                    Dec 31, 2025              │
│  📁 2025-Q1                                    Jan 18, 2026              │
│  ─────────────────────────────────────────────────────────────────────  │
│                                                                          │
│  [+ New Folder]                                                         │
│                                                                          │
│  Files to export:                                                        │
│  • P&ID-001_Rev-A.dwg                                                   │
│  • P&ID-001_Equipment-List.xlsx                                         │
│  • P&ID-001_Line-List.xlsx                                              │
│                                                                          │
│  [Cancel]                                              [Export to Folder]│
└─────────────────────────────────────────────────────────────────────────┘
```

## OAuth Integration

### Microsoft (OneDrive/SharePoint)
```yaml
Provider: Microsoft Identity Platform
Scopes:
  - openid
  - profile
  - email
  - Files.ReadWrite.All        # OneDrive
  - Sites.ReadWrite.All        # SharePoint
Token Endpoint: https://login.microsoftonline.com/common/oauth2/v2.0/token
Redirect URI: https://app.flowex.eu/auth/callback/microsoft
```

### Google Drive
```yaml
Provider: Google OAuth 2.0
Scopes:
  - openid
  - profile
  - email
  - https://www.googleapis.com/auth/drive.file
Token Endpoint: https://oauth2.googleapis.com/token
Redirect URI: https://app.flowex.eu/auth/callback/google
```

## Data Model

```typescript
interface CloudConnection {
  id: string;
  userId: string;
  organizationId: string;
  provider: 'onedrive' | 'sharepoint' | 'google_drive';
  accountEmail: string;
  accountName: string;
  accessToken: string;          // Encrypted
  refreshToken: string;         // Encrypted
  tokenExpiresAt: Date;
  siteId?: string;              // SharePoint site ID
  driveId?: string;             // Specific drive ID
  connectedAt: Date;
  lastUsedAt: Date;
}

interface CloudFile {
  id: string;                   // Provider's file ID
  name: string;
  path: string;
  size: number;
  mimeType: string;
  modifiedAt: Date;
  thumbnailUrl?: string;
}

interface CloudFolder {
  id: string;
  name: string;
  path: string;
  childCount: number;
}
```

## API Endpoints

### Connections
```
GET /api/v1/cloud/connections
Response: List of connected accounts

POST /api/v1/cloud/connections/{provider}/connect
Response: OAuth redirect URL

GET /api/v1/cloud/connections/callback/{provider}
Query: ?code=xxx&state=xxx
Response: Redirect to app with success/error

DELETE /api/v1/cloud/connections/{connectionId}
Response: 204 No Content
```

### File Operations
```
GET /api/v1/cloud/connections/{connectionId}/browse
Query: ?folderId=xxx
Response: {
  "currentFolder": CloudFolder,
  "folders": CloudFolder[],
  "files": CloudFile[]
}

GET /api/v1/cloud/connections/{connectionId}/search
Query: ?query=P&ID&type=pdf
Response: CloudFile[]

POST /api/v1/cloud/connections/{connectionId}/import
Request: {
  "fileIds": ["file-id-1", "file-id-2"],
  "projectId": "project-uuid"
}
Response: {
  "jobId": "uuid",
  "status": "processing",
  "fileCount": 2
}

POST /api/v1/cloud/connections/{connectionId}/export
Request: {
  "drawingId": "drawing-uuid",
  "folderId": "destination-folder-id",
  "files": ["dwg", "equipment_list", "line_list"]
}
Response: {
  "jobId": "uuid",
  "status": "processing"
}
```

## Implementation

### Microsoft Graph API
```python
from msgraph.core import GraphClient
from azure.identity import ClientSecretCredential

async def browse_onedrive(connection: CloudConnection, folder_id: str = None):
    """Browse OneDrive folder contents."""
    client = get_graph_client(connection)
    
    if folder_id:
        endpoint = f"/me/drive/items/{folder_id}/children"
    else:
        endpoint = "/me/drive/root/children"
    
    response = await client.get(endpoint)
    
    folders = []
    files = []
    
    for item in response.json()["value"]:
        if "folder" in item:
            folders.append(CloudFolder(
                id=item["id"],
                name=item["name"],
                path=item["parentReference"]["path"],
                childCount=item["folder"]["childCount"]
            ))
        elif "file" in item:
            files.append(CloudFile(
                id=item["id"],
                name=item["name"],
                path=item["parentReference"]["path"],
                size=item["size"],
                mimeType=item["file"]["mimeType"],
                modifiedAt=item["lastModifiedDateTime"]
            ))
    
    return folders, files

async def download_file(connection: CloudConnection, file_id: str) -> bytes:
    """Download file content from OneDrive."""
    client = get_graph_client(connection)
    response = await client.get(f"/me/drive/items/{file_id}/content")
    return response.content

async def upload_file(
    connection: CloudConnection,
    folder_id: str,
    filename: str,
    content: bytes
):
    """Upload file to OneDrive folder."""
    client = get_graph_client(connection)
    
    # For files < 4MB, use simple upload
    if len(content) < 4 * 1024 * 1024:
        await client.put(
            f"/me/drive/items/{folder_id}:/{filename}:/content",
            content=content
        )
    else:
        # Use upload session for larger files
        await upload_large_file(client, folder_id, filename, content)
```

### Google Drive API
```python
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

async def browse_google_drive(connection: CloudConnection, folder_id: str = None):
    """Browse Google Drive folder contents."""
    service = get_drive_service(connection)
    
    query = f"'{folder_id or 'root'}' in parents and trashed = false"
    
    results = service.files().list(
        q=query,
        fields="files(id, name, mimeType, size, modifiedTime, parents)",
        orderBy="folder,name"
    ).execute()
    
    folders = []
    files = []
    
    for item in results.get("files", []):
        if item["mimeType"] == "application/vnd.google-apps.folder":
            folders.append(CloudFolder(
                id=item["id"],
                name=item["name"],
                path="",  # Google Drive doesn't expose full path easily
                childCount=0
            ))
        else:
            files.append(CloudFile(
                id=item["id"],
                name=item["name"],
                path="",
                size=int(item.get("size", 0)),
                mimeType=item["mimeType"],
                modifiedAt=item["modifiedTime"]
            ))
    
    return folders, files
```

## Token Management

### Refresh Token Flow
```python
async def refresh_connection_token(connection: CloudConnection) -> CloudConnection:
    """Refresh expired access token using refresh token."""
    
    if connection.provider == "onedrive":
        token_data = await refresh_microsoft_token(connection.refresh_token)
    elif connection.provider == "google_drive":
        token_data = await refresh_google_token(connection.refresh_token)
    
    # Update connection with new tokens
    connection.access_token = encrypt(token_data["access_token"])
    if "refresh_token" in token_data:
        connection.refresh_token = encrypt(token_data["refresh_token"])
    connection.token_expires_at = datetime.utcnow() + timedelta(
        seconds=token_data["expires_in"]
    )
    
    await db.commit()
    return connection

async def get_valid_token(connection: CloudConnection) -> str:
    """Get valid access token, refreshing if needed."""
    if connection.token_expires_at < datetime.utcnow() + timedelta(minutes=5):
        connection = await refresh_connection_token(connection)
    
    return decrypt(connection.access_token)
```

## Acceptance Criteria

1. Users can connect Microsoft OneDrive accounts
2. Users can connect SharePoint sites
3. Users can connect Google Drive accounts
4. Users can browse folders in connected storage
5. Users can search for files by name
6. Users can import PDF files from cloud storage
7. Users can export results to cloud storage
8. Tokens auto-refresh without re-authentication
9. Users can disconnect accounts
10. Multiple files can be imported in batch
11. Multiple files can be exported in batch
12. File operations show progress indicators

## Error Handling

| Error | User Message | Action |
|-------|--------------|--------|
| Token expired | "Please reconnect your account" | Prompt reconnection |
| Permission denied | "Access denied to this file/folder" | Show error, suggest permissions |
| File not found | "File no longer exists" | Remove from list |
| Network error | "Connection failed. Retry?" | Offer retry |
| Rate limited | "Too many requests. Please wait." | Show countdown |
| Storage full | "Not enough space in destination" | Show available space |

## Security Considerations

1. Tokens stored encrypted (AES-256)
2. Tokens never exposed to frontend
3. All API calls server-side
4. Minimal scopes requested
5. Token revocation on disconnect
6. Audit logging for all file operations
