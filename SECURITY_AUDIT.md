# Security Audit Report - Flowex

**Audit Date:** 2026-01-19
**Auditor:** Ralph (AI Security Audit)
**Scope:** Full codebase security review

---

## Executive Summary

| Category | Risk Level | Issues Found |
|----------|-----------|--------------|
| SQL Injection | LOW | 0 |
| XSS | LOW | 0 |
| Authentication | MEDIUM | 3 |
| Secrets | CRITICAL | 2 |
| CORS | MEDIUM | 1 |
| Input Validation | LOW | 2 |
| Dependencies | MEDIUM | 1 |
| **Overall** | **MEDIUM** | **9 issues** |

**Critical Actions Required:**
1. ✅ FIXED: JWT algorithm mismatch (HS256 vs RS256)
2. ✅ FIXED: Added redirect URI validation in auth endpoints
3. ⚠️ ACTION REQUIRED: Rotate Supabase credentials if `.env` was ever committed
4. ⚠️ ACTION REQUIRED: Configure production secrets (`JWT_SECRET_KEY`, `TOKEN_ENCRYPTION_KEY`)

---

## 1. SQL Injection Vulnerabilities

**Risk Level: LOW** ✅

### Findings

No SQL injection vulnerabilities detected. All database queries use SQLAlchemy ORM with parameterized queries.

**Evidence:**
- `backend/app/core/deps.py:45`: Uses ORM filter methods
  ```python
  user = db.query(User).filter(User.email == token.email).first()
  ```
- `backend/app/api/routes/projects.py:47`: Parameterized queries
  ```python
  query = db.query(Project).filter(Project.organization_id == current_user.organization_id)
  ```
- `backend/app/services/cloud/service.py:136-140`: SQLAlchemy select statements
  ```python
  result = await self.db.execute(
      select(CloudConnection).where(
          CloudConnection.id == connection_id,
          CloudConnection.user_id == user_id,
      )
  )
  ```

**Status:** PASS - All queries use ORM safely

---

## 2. XSS (Cross-Site Scripting) Vulnerabilities

**Risk Level: LOW** ✅

### Findings

No XSS vulnerabilities detected in the frontend React codebase.

**Verification:**
- No `dangerouslySetInnerHTML` usage found
- No direct `innerHTML` manipulation
- No `eval()` or `Function()` constructor usage
- All user input rendered through React's JSX (auto-escaped)
- TypeScript provides additional type safety

**Status:** PASS - React's default escaping protects against XSS

---

## 3. Authentication/Authorization Issues

**Risk Level: MEDIUM** ⚠️

### 3.1 JWT Algorithm Mismatch (FIXED)

**Location:** `backend/app/core/security.py:113` and `backend/app/core/config.py:40`

**Issue:** Configuration specified RS256 but code used HS256 for internal token creation.

**Fix Applied:** Updated `create_access_token()` to use `settings.JWT_ALGORITHM` from config.

**Note:** The main token verification uses Auth0 JWKS (RS256) correctly. The internal token creation function is only used for testing purposes.

### 3.2 In-Memory OAuth State Storage

**Location:** `backend/app/api/routes/cloud.py:112`

```python
_oauth_states: dict[str, dict] = {}  # In-memory storage
```

**Issue:**
- State stored in process memory, lost on restart
- Not shared across multiple server instances
- Potential race condition in load-balanced deployments

**Severity:** MEDIUM for production deployments

**Recommendation:** Use Redis for OAuth state storage in production:
```python
# Store in Redis with TTL
redis_client.setex(f"oauth_state:{state}", 300, json.dumps(state_data))
```

### 3.3 Redirect URI Validation (FIXED)

**Location:** `backend/app/api/routes/auth.py:43-61`

**Issue:** User-controlled `redirect_uri` passed directly to Auth0 without validation.

**Fix Applied:** Added allowlist validation for redirect URIs:
```python
ALLOWED_REDIRECT_URIS = [
    "http://localhost:5173",
    "http://localhost:3000",
    # Production URIs added via CORS_ORIGINS
]
```

---

## 4. Secrets in Code

**Risk Level: CRITICAL** 🔴

### 4.1 Default Development Secrets

**Location:** `backend/app/core/config.py:39, 67`

```python
JWT_SECRET_KEY: str = "dev-secret-key-change-in-production"
TOKEN_ENCRYPTION_KEY: str = ""  # Can cause runtime errors
```

**Status:** Expected for development, but production deployment MUST override these.

**Recommendation:** Add startup validation in production mode:
```python
if not settings.DEBUG:
    assert settings.JWT_SECRET_KEY != "dev-secret-key-change-in-production"
    assert settings.TOKEN_ENCRYPTION_KEY, "TOKEN_ENCRYPTION_KEY must be set"
```

### 4.2 .env File Protection

**Location:** `.gitignore`

**Status:** ✅ `.env` is properly listed in `.gitignore` (line 19)

**Recommendation:** If `.env` was ever committed historically, rotate ALL credentials:
- Supabase keys (SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY)
- Auth0 secrets (AUTH0_CLIENT_SECRET)
- Microsoft/Google OAuth secrets
- JWT_SECRET_KEY

---

## 5. CORS Configuration

**Risk Level: MEDIUM** ⚠️

### Current Configuration

**Location:** `backend/app/main.py:15-21`

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Issues:**
1. `allow_methods=["*"]` is overly permissive
2. `allow_headers=["*"]` could expose sensitive headers
3. Combined with `allow_credentials=True`, increases attack surface

**Recommendation for Production:**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)
```

---

## 6. Input Validation

**Risk Level: LOW** ✅

### 6.1 File Upload Validation ✅

**Location:** `backend/app/services/drawings.py:21-40`

```python
def validate_file(filename: str, content_type: str, file_size: int) -> None:
    # Extension check
    if ext not in ALLOWED_EXTENSIONS:
        raise FileValidationError(...)
    # Content type check
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise FileValidationError(...)
    # Size check (50MB limit)
    if file_size > MAX_FILE_SIZE:
        raise FileValidationError(...)
```

**Status:** PASS - Comprehensive file validation

### 6.2 Path Traversal Protection

**Location:** `backend/app/api/routes/exports.py:528-530`

**Current:** File paths generated internally, not user-controlled.

**Status:** Safe in current implementation

### 6.3 API Input Validation ✅

All API endpoints use Pydantic models for request validation:
- Type checking enforced
- Required fields validated
- UUID parameters validated at routing level

---

## 7. Dependency Security

**Risk Level: MEDIUM** ⚠️

### Python Dependencies

**Location:** `backend/requirements.txt`

| Package | Version | Status |
|---------|---------|--------|
| fastapi | 0.109.2 | Update recommended (0.115+) |
| python-jose | 3.3.0 | Monitor for CVEs |
| sqlalchemy | 2.0.25 | ✅ Good |
| cryptography | 42.0.2 | ✅ Good |

**Recommendation:** Run periodic security scans:
```bash
pip-audit
safety check
```

### Frontend Dependencies

**Location:** `frontend/package.json`

All major dependencies (React 18, Zustand 4, etc.) are recent versions.

**Recommendation:** Run periodic security scans:
```bash
npm audit
```

---

## 8. Additional Security Observations

### 8.1 Token Encryption ✅

**Location:** `backend/app/services/cloud/encryption.py`

Cloud connection tokens are properly encrypted at rest using Fernet symmetric encryption.

### 8.2 Database Connection Security ✅

**Location:** `backend/app/core/database.py`

- Uses environment variables for connection strings
- Connection pooling with health checks
- Proper SSL configuration for production

### 8.3 Error Message Exposure

**Location:** `backend/app/core/deps.py:26-37`

```python
raise HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail=str(e),  # Could leak implementation details
    ...
)
```

**Recommendation:** Use generic error messages in production:
```python
detail="Invalid or expired token"
```

---

## Remediation Checklist

### Immediate (Before Production)

- [ ] Set strong `JWT_SECRET_KEY` (32+ random bytes, base64 encoded)
- [ ] Set `TOKEN_ENCRYPTION_KEY` (use `Fernet.generate_key().decode()`)
- [ ] Configure production `CORS_ORIGINS` with specific domains
- [ ] Rotate all secrets if `.env` was ever committed to git
- [ ] Add production environment validation for required secrets

### Short-term

- [ ] Implement Redis-based OAuth state storage
- [ ] Restrict CORS methods and headers
- [ ] Update FastAPI to latest version
- [ ] Set up pip-audit/npm audit in CI pipeline
- [x] Add rate limiting to authentication endpoints - `a550134`

### Long-term

- [ ] Implement token blacklisting for logout
- [ ] Add security headers middleware (HSTS, CSP, etc.)
- [ ] Set up Web Application Firewall (WAF)
- [ ] Implement audit logging for sensitive operations
- [ ] Regular penetration testing

---

## Files Modified During Audit

1. `backend/app/core/security.py` - Fixed JWT algorithm usage
2. `backend/app/api/routes/auth.py` - Added redirect URI validation
3. `SECURITY_AUDIT.md` - This document (created)
4. `IMPLEMENTATION_PLAN.md` - Updated with audit completion

---

*This audit was performed by automated code analysis. A manual penetration test is recommended before production deployment.*
