# Spec: Project Dashboard

## Job to be Done
Provide Project Managers with an overview dashboard to track P&ID conversion progress across projects.

## Functional Requirements

### Dashboard Overview
| ID | Requirement | Priority |
|----|-------------|----------|
| DB-01 | Display project summary (total drawings, status breakdown) | Must-Have |
| DB-02 | Show progress percentage | Must-Have |
| DB-03 | List all drawings with status and actions | Must-Have |
| DB-04 | Filter drawings by status | Must-Have |
| DB-05 | Search drawings by name/number | Must-Have |
| DB-06 | Sort drawings by date, status, name | Must-Have |
| DB-07 | Batch export all completed drawings | Must-Have |
| DB-08 | Usage meter (P&IDs used vs plan limit) | Must-Have |
| DB-09 | Recent activity feed | Should-Have |

### Project Management
| ID | Requirement | Priority |
|----|-------------|----------|
| PM-01 | Create new projects | Must-Have |
| PM-02 | Edit project details | Must-Have |
| PM-03 | Archive/delete projects | Must-Have |
| PM-04 | Invite team members to projects | Must-Have |
| PM-05 | Set project permissions (view/edit) | Should-Have |

### User Management
| ID | Requirement | Priority |
|----|-------------|----------|
| UM-01 | View team members | Must-Have |
| UM-02 | Invite new users (by email) | Must-Have |
| UM-03 | Set user roles (admin, member, viewer) | Must-Have |
| UM-04 | Remove users from organization | Must-Have |
| UM-05 | User activity log | Should-Have |

### Usage & Billing
| ID | Requirement | Priority |
|----|-------------|----------|
| UB-01 | Show current plan details | Must-Have |
| UB-02 | Display P&IDs used this month | Must-Have |
| UB-03 | Display remaining P&IDs | Must-Have |
| UB-04 | Upgrade plan button | Must-Have |
| UB-05 | Billing history | Should-Have |

## User Interface Design

### Main Dashboard
```
┌─────────────────────────────────────────────────────────────────────────────┐
│  FLOWEX                                              [Search] [Anna M. ▼]   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │  PROJECT: Waste-to-Energy Plant Alpha                   [⚙ Settings]   ││
│  │  Created: Jan 5, 2026  •  24 team members  •  48 drawings              ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                              │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐       │
│  │      24      │ │       8      │ │      12      │ │       4      │       │
│  │   Complete   │ │   In Review  │ │  Processing  │ │   Uploaded   │       │
│  │   ██████     │ │   ██████     │ │   ██████     │ │   ██████     │       │
│  │   50%        │ │   17%        │ │   25%        │ │   8%         │       │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘       │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │  DRAWINGS                                    [+ Upload] [↓ Export All] ││
│  │  ─────────────────────────────────────────────────────────────────────  ││
│  │  Status: [All ▼]                                    🔍 Search...        ││
│  │  ─────────────────────────────────────────────────────────────────────  ││
│  │  □  Drawing              Status        Progress    Updated      Actions ││
│  │  ─────────────────────────────────────────────────────────────────────  ││
│  │  □  P&ID-001 Rev A      ● Complete     100%        2h ago       [↓][⋮] ││
│  │  □  P&ID-002 Rev B      ○ Review       85%         1h ago       [→][⋮] ││
│  │  □  P&ID-003 Rev A      ◐ Processing   40%         30m ago      [⋮]    ││
│  │  □  P&ID-004 Rev A      ○ Uploaded     0%          15m ago      [▶][⋮] ││
│  │  ─────────────────────────────────────────────────────────────────────  ││
│  │  Showing 4 of 48 drawings                          < 1 2 3 ... 12 >    ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                              │
│  ┌─────────────────────────────────┐  ┌────────────────────────────────────┐│
│  │  USAGE THIS MONTH               │  │  RECENT ACTIVITY                   ││
│  │  ─────────────────────────      │  │  ────────────────────────────────  ││
│  │                                 │  │  Anna verified P&ID-001      2h    ││
│  │  ████████████░░░░  32/50 P&IDs  │  │  Erik uploaded P&ID-004      15m   ││
│  │                                 │  │  System completed P&ID-005   1d    ││
│  │  Professional Plan              │  │  Maria started review        1d    ││
│  │  Resets: Feb 1, 2026            │  │                                    ││
│  │  [Upgrade Plan]                 │  │  [View All →]                      ││
│  └─────────────────────────────────┘  └────────────────────────────────────┘│
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Status Icons and Actions
| Status | Icon | Color | Available Actions |
|--------|------|-------|-------------------|
| Uploaded | ○ | Gray | Start processing, Delete |
| Processing | ◐ | Blue | View progress, Cancel |
| Review | ○ | Orange | Open validation, Delete |
| Complete | ● | Green | Download, Export, Re-validate |
| Error | ✗ | Red | Retry, View error, Delete |

## Data Model

```typescript
interface Project {
  id: string;
  organizationId: string;
  name: string;
  description?: string;
  createdBy: string;
  createdAt: Date;
  updatedAt: Date;
  drawingCount: number;
  memberCount: number;
}

interface ProjectMember {
  id: string;
  projectId: string;
  userId: string;
  role: 'owner' | 'editor' | 'viewer';
  addedAt: Date;
  addedBy: string;
}

interface DrawingSummary {
  id: string;
  projectId: string;
  drawingNumber: string;
  revision: string;
  title: string;
  status: DrawingStatus;
  progress: number;          // 0-100
  updatedAt: Date;
  createdBy: string;
}

interface UsageStats {
  organizationId: string;
  periodStart: Date;
  periodEnd: Date;
  planLimit: number;
  usedCount: number;
  remainingCount: number;
}

interface ActivityItem {
  id: string;
  projectId: string;
  userId: string;
  userName: string;
  action: ActivityAction;
  entityType: 'drawing' | 'project' | 'user';
  entityId: string;
  entityName: string;
  timestamp: Date;
}

type ActivityAction = 
  | 'uploaded'
  | 'started_processing'
  | 'completed_processing'
  | 'started_validation'
  | 'completed_validation'
  | 'exported'
  | 'deleted'
  | 'invited_user'
  | 'removed_user';
```

## API Endpoints

### Projects

```
GET /api/v1/projects
Response: List of projects for current organization

POST /api/v1/projects
Request: { name, description }
Response: Created project

GET /api/v1/projects/{id}
Response: Project details with summary stats

PATCH /api/v1/projects/{id}
Request: { name?, description? }
Response: Updated project

DELETE /api/v1/projects/{id}
Response: 204 No Content
```

### Project Drawings

```
GET /api/v1/projects/{id}/drawings
Query: ?status=review&page=1&limit=20&sort=updatedAt&order=desc

Response:
{
  "items": [DrawingSummary],
  "total": 48,
  "page": 1,
  "limit": 20,
  "statusCounts": {
    "uploaded": 4,
    "processing": 12,
    "review": 8,
    "complete": 24,
    "error": 0
  }
}
```

### Project Members

```
GET /api/v1/projects/{id}/members
Response: List of project members

POST /api/v1/projects/{id}/members
Request: { email, role }
Response: Invited member (sends email)

DELETE /api/v1/projects/{id}/members/{userId}
Response: 204 No Content
```

### Usage

```
GET /api/v1/organizations/{id}/usage
Response:
{
  "periodStart": "2026-01-01",
  "periodEnd": "2026-01-31",
  "plan": "professional",
  "planLimit": 35,
  "usedCount": 32,
  "remainingCount": 3,
  "extraDrawingRate": 6.00
}
```

### Activity Feed

```
GET /api/v1/projects/{id}/activity
Query: ?limit=10

Response:
{
  "items": [
    {
      "id": "uuid",
      "userName": "Anna Müller",
      "action": "completed_validation",
      "entityType": "drawing",
      "entityName": "P&ID-001",
      "timestamp": "2026-01-18T10:30:00Z"
    }
  ]
}
```

## Acceptance Criteria

1. Dashboard loads within 3 seconds
2. Status counts update in real-time (or near real-time via polling)
3. User can filter drawings by status
4. User can search drawings by name/number
5. User can sort drawings by date, status, name
6. User can batch export all completed drawings
7. Usage meter accurately shows plan usage
8. User can create and manage projects
9. User can invite team members by email
10. Activity feed shows recent actions

## Performance Requirements

| Metric | Target |
|--------|--------|
| Dashboard load time | <3 seconds |
| Drawing list pagination | <500ms |
| Search results | <1 second |
| Real-time status updates | <5 second delay |

## Role Permissions

| Action | Admin | Member | Viewer |
|--------|-------|--------|--------|
| View dashboard | ✓ | ✓ | ✓ |
| Upload drawings | ✓ | ✓ | ✗ |
| Validate drawings | ✓ | ✓ | ✗ |
| Export drawings | ✓ | ✓ | ✓ |
| Delete drawings | ✓ | ✓ | ✗ |
| Create projects | ✓ | ✗ | ✗ |
| Manage members | ✓ | ✗ | ✗ |
| View usage/billing | ✓ | ✗ | ✗ |
| Upgrade plan | ✓ | ✗ | ✗ |
