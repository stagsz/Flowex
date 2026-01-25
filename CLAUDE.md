# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Flowex is an AI-powered P&ID (Piping & Instrumentation Diagram) digitization platform. It converts legacy PDF P&IDs into editable AutoCAD drawings (DWG/DXF) and structured engineering data lists using computer vision and OCR.

**Status:** Phase 8 in progress (80%) - Production deployed, beta testing ready.

**Production URLs:**
- Backend: https://flowex-production-30eb.up.railway.app
- Frontend: https://frontend-xi-seven-28.vercel.app

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 18, TypeScript 5, Tailwind CSS, shadcn/ui, Zustand, Vitest, Playwright |
| Backend | Python 3.11, FastAPI, SQLAlchemy 2.0, Celery, pytest |
| Database | PostgreSQL 15 (Supabase), Redis (cache/tasks) |
| AI/ML | PyTorch 2.2+ (ResNet-50 + FPN), Tesseract 5.x (OCR) |
| Storage | Supabase Storage (dev/prod) / AWS S3 (optional) |
| Auth | Supabase Auth or Auth0 (Microsoft/Google SSO) |
| CAD Export | ezdxf |
| Deployment | Railway (backend), Vercel (frontend), Upstash (Redis) |

## Build Commands

### Frontend
```bash
cd frontend
npm install && npm run dev          # Start dev server (localhost:5173)
npm run typecheck && npm run lint && npm run test  # Pre-commit checks
npm run e2e                          # Run Playwright E2E tests
```

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload       # Start dev server (localhost:8000)
mypy app && ruff check app && pytest  # Pre-commit checks
```

### Database
```bash
docker-compose up -d postgres redis  # Start local services
alembic upgrade head                 # Apply migrations
alembic revision --autogenerate -m "description"  # New migration
```

### ML Pipeline
```bash
cd ml
python training/train.py             # Train CNN
python training/synthetic_generator.py  # Generate training data
```

## Project Structure

```
flowex/
├── frontend/               # React 18 + TypeScript 5 application
│   ├── src/
│   │   ├── components/     # UI components (cloud, export, feedback, layout, ui)
│   │   ├── pages/          # 10 page components
│   │   ├── stores/         # Zustand stores (authStore, cloudStore)
│   │   ├── lib/            # Utilities (api, supabase, symbol-classes)
│   │   └── App.tsx
│   ├── tests/              # Vitest unit tests
│   └── e2e/                # Playwright E2E tests
│
├── backend/                # FastAPI + SQLAlchemy application
│   ├── app/
│   │   ├── api/routes/     # 8 route modules (39+ endpoints)
│   │   ├── core/           # Config, database, security, Celery
│   │   ├── models/         # 12 SQLAlchemy ORM models
│   │   ├── services/       # Business logic (audit, export, storage, cloud)
│   │   ├── tasks/          # Celery background jobs
│   │   └── ml/             # ML integration layer
│   ├── alembic/            # Database migrations (5 versions)
│   └── tests/              # 17 pytest test modules (316 tests)
│
├── ml/                     # Machine learning pipeline
│   ├── models/             # Trained model weights
│   └── training/           # Training scripts, dataset, symbol classes
│
├── spec/                   # 9 feature specification documents
├── docs/                   # Deployment and setup guides
├── ecs/                    # AWS ECS task definitions
├── .github/                # GitHub Actions workflows
├── PRD.json                # Product requirements (machine-readable)
├── IMPLEMENTATION_PLAN.md  # Task breakdown and progress
└── PROGRESS.md             # Overall progress tracking
```

## Architecture

**Data Flow:**
```
PDF Upload → Storage (Supabase/S3) → PDF Processing (Celery) → Symbol Detection (CNN) → OCR (Tesseract)
    ↓
Validation Interface (side-by-side) ← Human Review
    ↓
Export → AutoCAD DXF + Data Lists (Equipment, Line, Instrument, Valve, MTO)
```

**Key Patterns:**
- FastAPI async endpoints with SQLAlchemy ORM
- Background jobs via Celery + Redis for file processing
- JWT authentication with Supabase or Auth0
- Organization-based multi-tenancy with RBAC
- ISO 10628 standard for P&ID symbols (50 classes)
- Rate limiting on auth endpoints (slowapi)
- Security headers middleware (OWASP recommended)
- Redis-based OAuth state storage (CSRF protection)
- Fernet encryption for cloud OAuth tokens
- Audit logging for compliance

## API Routes (8 Modules, 39+ Endpoints)

| Module | Key Endpoints | Purpose |
|--------|---------------|---------|
| `auth.py` | /login, /callback, /refresh, /logout, /me | OAuth 2.0 authentication |
| `drawings.py` | /upload, /symbols/*, /lines/*, /process | File upload, symbol CRUD |
| `exports.py` | /dxf, /lists, /checklist, /compare | Export generation |
| `projects.py` | CRUD operations | Project management |
| `organizations.py` | /users, /invites, /audit-logs | Team & compliance |
| `users.py` | /me, /data-export | User profile, GDPR |
| `cloud.py` | /connect, /browse, /import, /export | Cloud integrations |
| `feedback.py` | POST, GET, /stats | Beta feedback |

## Database Models (12 Tables)

- `User` - Auth0/Supabase user with organization membership
- `Organization` - Multi-tenant container with RBAC
- `OrganizationInvite` - Pending user invitations
- `Project` - Project container with metadata
- `Drawing` - PDF file with processing status
- `Symbol` - Detected P&ID symbols (50 ISO 10628 classes)
- `Line` - Process/equipment line connections
- `TextAnnotation` - Extracted text with position
- `CloudConnection` - OAuth tokens (encrypted)
- `AuditLog` - User activity logging
- `BetaFeedback` - User feedback collection

## Frontend Pages

| Page | Route | Purpose |
|------|-------|---------|
| LoginPage | /login | Auth0/Supabase SSO |
| DashboardPage | / | Overview with stats |
| ProjectsPage | /projects | Project management |
| DrawingsPage | /projects/:id | Drawing list with sorting |
| UploadPage | /upload | PDF upload (drag-drop) |
| ValidationPage | /validate/:id | Side-by-side validation |
| SettingsIntegrationsPage | /settings/integrations | Cloud connections |
| AuditLogsPage | /admin/audit-logs | Admin audit viewer |
| BetaAdminPage | /admin/beta | Beta feedback dashboard |

## Development Workflow

This project uses the "Ralph" autonomous AI methodology:
1. One task per iteration
2. Tests must pass before committing (`mypy app && ruff check app && pytest`)
3. Follow existing code patterns
4. Update IMPLEMENTATION_PLAN.md after each task
5. Keep commits atomic and well-described

## Test Coverage

**Backend (316 tests):**
- Authentication, drawings, exports, projects, organizations
- GDPR endpoints, cloud integrations, audit logging
- ML pipeline, PDF processing, security headers

**Frontend (18 tests):**
- Auth store (login, logout, checkAuth, DEV_AUTH_BYPASS)
- Main App component rendering

## Key Files to Read First

1. **IMPLEMENTATION_PLAN.md** - Current task queue and progress
2. **PROGRESS.md** - Overall project status (95% complete)
3. **spec/*.md** - 9 detailed feature specifications
4. **PRD.json** - Full product requirements
5. **docs/BETA_TESTING_GUIDE.md** - Beta testing checklist

## Code Conventions

**Backend (Python):**
- Use Pydantic V2 `model_config = ConfigDict(...)` syntax
- Use `datetime.now(UTC)` instead of deprecated `datetime.utcnow()`
- Add type annotations; run `mypy app` before committing
- Use `ruff check app` for linting
- Celery tasks need `# type: ignore[misc]` on decorators

**Frontend (TypeScript):**
- Use centralized `api.ts` for authenticated fetch calls
- Use Zustand for state management
- React Router v7 future flags enabled
- shadcn/ui components in `src/components/ui/`

## Known Pitfalls

- **PDF processing:** Large files need chunking via Celery background jobs
- **OCR accuracy:** Pre-process scanned images (deskew, denoise, binarize)
- **File storage:** Always use EU region (eu-west-1) for GDPR
- **Auth tokens:** JWT expires based on provider settings; implement refresh logic
- **API URLs:** Frontend must use `/api/v1/` prefix (not `/api/`)
- **Mypy ignores:** Type ignore codes vary by environment (`misc` vs `untyped-decorator`)
- **Redis types:** Some environments need `# type: ignore[no-untyped-call]` on `redis.from_url()`

## Environment Variables

**Frontend (.env):**
```bash
VITE_API_URL=http://localhost:8000
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=xxx
VITE_DEV_AUTH_BYPASS=false  # Set true for local dev without auth
```

**Backend (.env):**
```bash
# Auth (choose one provider)
AUTH_PROVIDER=supabase  # or "auth0"
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=xxx
SUPABASE_JWT_SECRET=xxx

# Auth0 (if using)
AUTH0_DOMAIN=your-domain.auth0.com
AUTH0_CLIENT_ID=xxx
AUTH0_CLIENT_SECRET=xxx

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/flowex

# Storage
STORAGE_PROVIDER=supabase  # or "aws"
SUPABASE_STORAGE_BUCKET=drawings
AWS_S3_BUCKET=flowex-uploads-eu  # if using AWS
AWS_REGION=eu-west-1

# Cloud Integrations
MICROSOFT_CLIENT_ID=xxx
MICROSOFT_CLIENT_SECRET=xxx
GOOGLE_CLIENT_ID=xxx
GOOGLE_CLIENT_SECRET=xxx

# Redis
REDIS_URL=redis://localhost:6379/0

# Security (production only)
JWT_SECRET_KEY=xxx  # Required in production
TOKEN_ENCRYPTION_KEY=xxx  # Required in production

# Rate Limiting
RATE_LIMIT_LOGIN=10/minute
RATE_LIMIT_CALLBACK=20/minute
RATE_LIMIT_REFRESH=30/minute

# Monitoring
SENTRY_DSN=xxx
```

## Deployment

**Supabase Stack (Recommended for development/small teams):**
- Backend: Railway
- Frontend: Vercel
- Database/Auth/Storage: Supabase
- Redis: Upstash
- Cost: $0-25/month

**AWS Stack (Production/enterprise):**
- Infrastructure: Terraform (VPC, ECS, RDS, ElastiCache, S3, CloudFront)
- CI/CD: GitHub Actions
- Cost: $60-100/month

See `docs/DEPLOYMENT.md` and `docs/SUPABASE_DEPLOYMENT.md` for detailed guides.

## Security Features

- **Authentication:** Supabase or Auth0 SSO (Microsoft/Google)
- **Authorization:** Organization-based RBAC (owner, admin, member, viewer)
- **Rate Limiting:** slowapi on auth endpoints
- **Security Headers:** OWASP recommended headers (X-Frame-Options, CSP, HSTS)
- **OAuth State:** Redis-backed with CSRF protection and replay prevention
- **Token Encryption:** Fernet for cloud OAuth tokens
- **Audit Logging:** All user actions logged for compliance
- **GDPR:** Data export (Article 15) and account deletion (Article 17)

## Recent Changes (Last Updated: 2026-01-23)

- **SEC-04:** Audit log viewer admin page with filtering and CSV export
- **DB-06:** Drawing list sorting (name, date, status)
- **VAL-06:** Component list sorting (tag, type, confidence, status)
- **PM-03:** Project archive and delete confirmation dialog
- **PM-02:** Edit project functionality
- **DB-01:** Drawing count in project API responses
- **Beta Admin:** Dashboard for monitoring pilot feedback
- **GDPR:** User data export and account deletion endpoints

See `IMPLEMENTATION_PLAN.md` for complete change history.
