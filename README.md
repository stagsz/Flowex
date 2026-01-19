# Flowex

AI-powered P&ID digitization platform that converts legacy PDF P&IDs into intelligent AutoCAD drawings and structured engineering data lists.

## Overview

Flowex uses computer vision and OCR to automatically detect symbols, extract text, and reconstruct P&ID (Piping & Instrumentation Diagram) drawings. Engineers can validate AI results through a side-by-side interface before exporting to AutoCAD DWG/DXF format or generating equipment lists, line lists, and other engineering documents.

**Target Market:** Mid-size EPC firms (50-200 employees) in Waste-to-Energy and Environmental Services sectors across Europe.

## Features

- **PDF Upload** - Support for vector and scanned PDFs up to 50MB
- **AI Symbol Detection** - CNN-based detection of 50 ISO 10628 symbol classes (equipment, instruments, valves)
- **OCR Text Extraction** - Tesseract-based extraction of equipment tags, instrument tags, and line numbers
- **Validation Interface** - Side-by-side comparison with synchronized zoom/pan and human-in-the-loop editing
- **AutoCAD Export** - DWG/DXF output with proper layers and editable symbol blocks
- **Data List Exports** - Equipment List, Line List, Instrument List, Valve List, MTO (Excel, CSV, PDF)
- **Cloud Storage Integration** - OneDrive, SharePoint, Google Drive
- **SSO Authentication** - Microsoft Azure AD and Google Workspace

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 18, TypeScript 5, Tailwind CSS, shadcn/ui, Zustand |
| Backend | Python 3.11, FastAPI, SQLAlchemy |
| Database | PostgreSQL 15, Redis |
| AI/ML | PyTorch 2.x (ResNet-50 + FPN), Tesseract 5.x |
| Storage | Supabase Storage (dev) / AWS S3 (prod) |
| Auth | Auth0 (OAuth 2.0 / OIDC) |
| CAD Export | ezdxf |
| Infrastructure | Docker, Kubernetes, GitHub Actions |

## Getting Started

### Prerequisites

- Node.js 18+
- Python 3.11+
- PostgreSQL 15+
- Redis
- Docker & Docker Compose (recommended)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/your-org/flowex.git
cd flowex
```

2. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. Start services with Docker:
```bash
docker-compose up -d
```

4. Set up the frontend:
```bash
cd frontend
npm install
npm run dev
```

5. Set up the backend:
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

### Environment Variables

The application supports two storage backends - Supabase (recommended for development) and AWS S3 (for production).

**Option A: Supabase (Development)**

See [docs/SUPABASE_SETUP.md](docs/SUPABASE_SETUP.md) for detailed setup instructions.

```bash
# Storage Provider
STORAGE_PROVIDER=supabase

# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
SUPABASE_STORAGE_BUCKET=drawings

# Database (Supabase PostgreSQL)
DATABASE_URL=postgresql://postgres.xxx:[password]@aws-0-eu-west-1.pooler.supabase.com:6543/postgres
```

**Option B: AWS (Production)**

```bash
# Storage Provider
STORAGE_PROVIDER=aws

# AWS Configuration
AWS_S3_BUCKET=flowex-uploads-eu
AWS_REGION=eu-west-1
AWS_ACCESS_KEY_ID=xxx
AWS_SECRET_ACCESS_KEY=xxx

# Database (AWS RDS or local)
DATABASE_URL=postgresql://user:pass@localhost:5432/flowex
```

**Common Configuration**

```bash
# Authentication
AUTH0_DOMAIN=your-domain.auth0.com
AUTH0_CLIENT_ID=xxx
AUTH0_CLIENT_SECRET=xxx

# Redis (for background tasks)
REDIS_URL=redis://localhost:6379/0

# Optional
SENTRY_DSN=xxx
LOG_LEVEL=INFO
```

## Development

### Frontend

```bash
cd frontend
npm run dev          # Development server (localhost:5173)
npm run build        # Production build
npm run typecheck    # TypeScript checking
npm run lint         # ESLint
npm run test         # Run tests
```

### Backend

```bash
cd backend
uvicorn app.main:app --reload    # Dev server (localhost:8000)
pytest                           # Run tests
pytest --cov=app                 # With coverage
mypy app                         # Type checking
ruff check app                   # Linting
ruff format app                  # Formatting
```

### Database Migrations

```bash
alembic upgrade head                              # Apply migrations
alembic revision --autogenerate -m "description"  # Create migration
```

### ML Pipeline

```bash
cd ml
python training/train_symbol_detector.py  # Train model
python training/evaluate.py               # Evaluate model
```

### Ralph (Autonomous AI Loop)

Ralph is an autonomous AI coding loop based on [Geoff Huntley's methodology](https://ghuntley.com/ralph/). It runs Claude Code in a loop to automatically implement tasks from the implementation plan.

**Prerequisites:**
- [Claude Code CLI](https://claude.ai/code) installed and authenticated

**Usage:**

```bash
# Planning mode - generate/update IMPLEMENTATION_PLAN.md
./loop.sh plan

# Building mode - implement tasks from the plan (unlimited iterations)
./loop.sh build

# Building mode with iteration limit
./loop.sh build 20
./loop.sh 20        # Shorthand for build mode with 20 iterations
```

**Modes:**
- **Planning mode:** Analyzes specs and generates/updates the implementation plan
- **Building mode:** Picks the next task from the plan, implements it, commits, and repeats

**Files used by Ralph:**
- `PROMPT_Plan.md` - Instructions for planning mode
- `PROMPT_Build.md` - Instructions for building mode
- `AGENTS.md` - Operational reference for the AI
- `IMPLEMENTATION_PLAN.md` - Task queue (updated by Ralph)

**Logs:** Each session logs to `ralph_log_YYYYMMDD.txt`

Press `Ctrl+C` to stop the loop at any time.

## Project Structure

```
flowex/
├── frontend/               # React application
│   ├── src/
│   │   ├── components/     # UI components
│   │   ├── pages/          # Page components
│   │   ├── hooks/          # Custom hooks
│   │   ├── lib/            # Utilities
│   │   └── types/          # TypeScript types
│   └── tests/
├── backend/                # FastAPI application
│   ├── app/
│   │   ├── api/            # API routes
│   │   ├── core/           # Config, security
│   │   ├── models/         # SQLAlchemy models
│   │   ├── services/       # Business logic
│   │   └── ml/             # AI/ML pipeline
│   └── tests/
├── ml/                     # Model training
│   ├── data/               # Training data
│   ├── models/             # Saved models
│   └── training/           # Training scripts
├── spec/                   # Feature specifications
├── PRD.json                # Product requirements
├── IMPLEMENTATION_PLAN.md  # Development roadmap
└── AGENTS.md               # Development guide
```

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────────────┐
│   Frontend  │────▶│   Backend   │────▶│     PostgreSQL      │
│   (React)   │◀────│  (FastAPI)  │◀────│ (Supabase or Local) │
└─────────────┘     └──────┬──────┘     └─────────────────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │ Storage  │ │  Celery  │ │   ML     │
        │ Supabase │ │  Workers │ │ Pipeline │
        │ or S3    │ │  + Redis │ │          │
        └──────────┘ └──────────┘ └──────────┘
```

**Processing Flow:**
1. User uploads PDF P&ID
2. File stored in Supabase/S3, job queued in Celery
3. PDF processed (vector extraction or image conversion)
4. CNN detects symbols, Tesseract extracts text
5. Results stored in database
6. User validates in side-by-side interface
7. Export to AutoCAD or data lists

## API Documentation

When running locally, API documentation is available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Testing

```bash
# Run all tests
cd frontend && npm test
cd backend && pytest

# Pre-commit checks
cd frontend && npm run typecheck && npm run lint && npm run test
cd backend && mypy app && ruff check app && pytest
```

## Security & Compliance

- **Authentication:** SSO via Auth0 (Microsoft, Google)
- **Encryption:** TLS 1.3 in transit, AES-256 at rest
- **Data Residency:** EU regions only (GDPR compliant)
- **Audit Logging:** All significant actions logged

## License

Proprietary - All rights reserved.

## Support

For support inquiries, please contact the development team.
