# Spec: Authentication & Security

## Job to be Done
Provide secure SSO authentication and ensure GDPR compliance for European customers.

## Functional Requirements

### Authentication
| ID | Requirement | Priority |
|----|-------------|----------|
| AUTH-01 | SSO via Microsoft Azure AD | Must-Have |
| AUTH-02 | SSO via Google Workspace | Must-Have |
| AUTH-03 | Organization-based multi-tenancy | Must-Have |
| AUTH-04 | Role-based access control (RBAC) | Must-Have |
| AUTH-05 | Session management with JWT | Must-Have |
| AUTH-06 | Automatic session refresh | Must-Have |
| AUTH-07 | Session timeout (24 hours) | Must-Have |
| AUTH-08 | Logout from all devices | Should-Have |

### Security
| ID | Requirement | Priority |
|----|-------------|----------|
| SEC-01 | Data encryption in transit (TLS 1.3) | Must-Have |
| SEC-02 | Data encryption at rest (AES-256) | Must-Have |
| SEC-03 | EU data residency | Must-Have |
| SEC-04 | User activity audit logging | Must-Have |
| SEC-05 | Two-factor authentication (2FA) | Should-Have |
| SEC-06 | API rate limiting | Must-Have |
| SEC-07 | Input validation and sanitization | Must-Have |
| SEC-08 | CORS policy enforcement | Must-Have |

### GDPR Compliance
| ID | Requirement | Priority |
|----|-------------|----------|
| GDPR-01 | Data minimization (collect only necessary data) | Must-Have |
| GDPR-02 | Right to access (data export) | Must-Have |
| GDPR-03 | Right to deletion (account deletion) | Must-Have |
| GDPR-04 | Data processing agreement template | Must-Have |
| GDPR-05 | Privacy policy | Must-Have |
| GDPR-06 | Cookie consent management | Must-Have |
| GDPR-07 | Breach notification process | Must-Have |
| GDPR-08 | Data retention policies | Must-Have |

## Authentication Flow

### SSO Login Flow
```
┌─────────┐     ┌─────────┐     ┌─────────────┐     ┌─────────┐
│  User   │     │ Flowex  │     │  Auth0 /    │     │ MS/Google│
│ Browser │     │ Frontend│     │  Azure B2C  │     │   IdP    │
└────┬────┘     └────┬────┘     └──────┬──────┘     └────┬────┘
     │               │                  │                 │
     │ 1. Click Login│                  │                 │
     │──────────────>│                  │                 │
     │               │                  │                 │
     │               │ 2. Redirect to   │                 │
     │               │    Auth Provider │                 │
     │               │─────────────────>│                 │
     │               │                  │                 │
     │ 3. Redirect to│                  │                 │
     │    IdP Login  │                  │                 │
     │<─────────────────────────────────│                 │
     │               │                  │                 │
     │ 4. Enter Credentials             │                 │
     │──────────────────────────────────────────────────>│
     │               │                  │                 │
     │ 5. Auth Success + Code           │                 │
     │<──────────────────────────────────────────────────│
     │               │                  │                 │
     │ 6. Code       │                  │                 │
     │──────────────>│                  │                 │
     │               │                  │                 │
     │               │ 7. Exchange Code │                 │
     │               │    for Tokens    │                 │
     │               │─────────────────>│                 │
     │               │                  │                 │
     │               │ 8. ID Token +    │                 │
     │               │    Access Token  │                 │
     │               │<─────────────────│                 │
     │               │                  │                 │
     │               │ 9. Create/Update │                 │
     │               │    User Session  │                 │
     │               │                  │                 │
     │ 10. JWT Token │                  │                 │
     │<──────────────│                  │                 │
     │               │                  │                 │
```

### JWT Token Structure
```json
{
  "header": {
    "alg": "RS256",
    "typ": "JWT"
  },
  "payload": {
    "sub": "user-uuid",
    "email": "anna.muller@epcfirm.eu",
    "name": "Anna Müller",
    "org_id": "org-uuid",
    "role": "member",
    "iat": 1737193200,
    "exp": 1737279600
  }
}
```

## Data Model

```typescript
interface User {
  id: string;
  organizationId: string;
  email: string;
  name: string;
  role: 'admin' | 'member' | 'viewer';
  ssoProvider: 'microsoft' | 'google';
  ssoId: string;              // External ID from IdP
  lastLoginAt: Date;
  createdAt: Date;
  updatedAt: Date;
}

interface Organization {
  id: string;
  name: string;
  slug: string;               // Unique URL-safe identifier
  subscriptionTier: 'starter' | 'professional' | 'business';
  monthlyPidLimit: number;
  ssoEnforced: boolean;       // Require SSO for all users
  allowedDomains: string[];   // Restrict to email domains
  createdAt: Date;
  updatedAt: Date;
}

interface Session {
  id: string;
  userId: string;
  token: string;              // JWT token
  refreshToken: string;
  ipAddress: string;
  userAgent: string;
  expiresAt: Date;
  createdAt: Date;
}

interface AuditLog {
  id: string;
  userId: string;
  organizationId: string;
  action: string;
  entityType: string;
  entityId: string;
  ipAddress: string;
  userAgent: string;
  metadata: Record<string, any>;
  timestamp: Date;
}
```

## Role-Based Access Control

### Roles and Permissions
| Permission | Admin | Member | Viewer |
|------------|-------|--------|--------|
| View drawings | ✓ | ✓ | ✓ |
| Upload drawings | ✓ | ✓ | ✗ |
| Process drawings | ✓ | ✓ | ✗ |
| Validate drawings | ✓ | ✓ | ✗ |
| Export drawings | ✓ | ✓ | ✓ |
| Delete drawings | ✓ | ✓ | ✗ |
| Create projects | ✓ | ✓ | ✗ |
| Delete projects | ✓ | ✗ | ✗ |
| Invite users | ✓ | ✗ | ✗ |
| Remove users | ✓ | ✗ | ✗ |
| Manage billing | ✓ | ✗ | ✗ |
| View audit logs | ✓ | ✗ | ✗ |

## API Security

### Rate Limiting
| Endpoint Type | Rate Limit |
|---------------|------------|
| Authentication | 10 requests/minute |
| API (general) | 100 requests/minute |
| Upload | 10 uploads/minute |
| Export | 20 exports/minute |

### CORS Configuration
```python
CORS_ORIGINS = [
    "https://app.flowex.eu",
    "https://staging.flowex.eu",
]

CORS_ALLOW_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE"]
CORS_ALLOW_HEADERS = ["Authorization", "Content-Type"]
CORS_ALLOW_CREDENTIALS = True
```

### API Authentication
```python
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer

security = HTTPBearer()

async def get_current_user(
    token: str = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    try:
        payload = jwt.decode(token, PUBLIC_KEY, algorithms=["RS256"])
        user = await db.get(User, payload["sub"])
        if not user:
            raise HTTPException(status_code=401)
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

## Data Protection

### Encryption
```yaml
In Transit:
  Protocol: TLS 1.3
  Certificates: Let's Encrypt (auto-renewal)
  HSTS: Enabled (max-age=31536000)

At Rest:
  Algorithm: AES-256-GCM
  Key Management: AWS KMS / Azure Key Vault
  Scope: All user data, files, and backups
```

### Data Residency
```yaml
Primary Region: eu-west-1 (Ireland) or West Europe (Netherlands)
Backup Region: eu-central-1 (Frankfurt)
Data Centers: EU only, SOC 2 certified
CDN: EU edge locations only
```

## GDPR Implementation

### Data Subject Rights

#### Right to Access
```
GET /api/v1/users/me/data-export

Response:
{
  "exportId": "uuid",
  "status": "processing",
  "downloadUrl": null,  // Available when complete
  "expiresAt": "2026-01-25T00:00:00Z"
}

// Export includes:
// - User profile data
// - All uploaded drawings (metadata)
// - Activity history
// - Exported in JSON + original files
```

#### Right to Deletion
```
DELETE /api/v1/users/me

Request:
{
  "confirmPhrase": "DELETE MY ACCOUNT",
  "reason": "optional feedback"
}

Response: 202 Accepted
{
  "deletionScheduledAt": "2026-01-25T00:00:00Z",
  "message": "Account will be deleted in 7 days. Cancel anytime before."
}

// 7-day grace period
// Anonymize data in backups
// Keep audit logs (anonymized) for compliance
```

### Data Retention
| Data Type | Retention Period | Deletion Process |
|-----------|------------------|------------------|
| User accounts | Until deletion | Anonymize on request |
| Project data | Until org deletion | Permanent delete |
| Uploaded drawings | 1 year after last access | Auto-archive, deletable |
| Processed outputs | 1 year after creation | Auto-archive, deletable |
| Audit logs | 3 years | Automated purge |
| Billing records | 7 years | Aggregated after 3 years |

### Privacy Policy Requirements
- Clear explanation of data collected
- Purpose of data processing
- Data sharing with third parties
- User rights under GDPR
- Contact information for DPO
- Cookie policy

## API Endpoints

### Authentication
```
POST /api/v1/auth/sso/microsoft
POST /api/v1/auth/sso/google
POST /api/v1/auth/refresh
POST /api/v1/auth/logout
```

### User Management
```
GET /api/v1/users/me
PATCH /api/v1/users/me
GET /api/v1/users/me/data-export
DELETE /api/v1/users/me
```

### Organization Users (Admin)
```
GET /api/v1/organizations/{id}/users
POST /api/v1/organizations/{id}/users/invite
PATCH /api/v1/organizations/{id}/users/{userId}
DELETE /api/v1/organizations/{id}/users/{userId}
```

### Audit Logs (Admin)
```
GET /api/v1/organizations/{id}/audit-logs
Query: ?startDate=2026-01-01&endDate=2026-01-31&userId=xxx&action=xxx
```

## Acceptance Criteria

1. Users can sign in via Microsoft SSO
2. Users can sign in via Google SSO
3. JWT tokens are issued on successful authentication
4. Tokens expire after 24 hours
5. Token refresh works without re-authentication
6. Users can only access their organization's data
7. Role permissions are enforced on all endpoints
8. All API requests require valid authentication
9. Rate limiting prevents abuse
10. Audit logs capture all significant actions
11. Users can export their personal data
12. Users can request account deletion
13. Data is encrypted in transit and at rest
14. All data resides in EU regions

## Security Checklist

- [ ] TLS 1.3 enabled on all endpoints
- [ ] HSTS header configured
- [ ] CORS properly restricted
- [ ] JWT tokens use RS256 algorithm
- [ ] Refresh tokens are securely stored
- [ ] Rate limiting on all endpoints
- [ ] Input validation on all inputs
- [ ] SQL injection prevention (parameterized queries)
- [ ] XSS prevention (output encoding)
- [ ] CSRF protection (where applicable)
- [ ] Security headers (X-Frame-Options, CSP, etc.)
- [ ] Dependency vulnerability scanning
- [ ] Regular security audits
