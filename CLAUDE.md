# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Flowex is an AI-powered P&ID (Piping & Instrumentation Diagram) digitization platform. It converts legacy PDF P&IDs into editable AutoCAD drawings (DWG/DXF) and structured engineering data lists using computer vision and OCR.

**Status:** Phase 6 complete - Export features implemented.

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 18, TypeScript 5, Tailwind CSS, shadcn/ui, Zustand, Vitest |
| Backend | Python 3.11, FastAPI, SQLAlchemy, pytest |
| Database | PostgreSQL 15 (Supabase or local), Redis (cache) |
| AI/ML | PyTorch 2.x (ResNet-50 + FPN), Tesseract 5.x (OCR) |
| Storage | Supabase Storage (dev) / AWS S3 (prod) |
| Auth | Auth0 (Microsoft/Google SSO) |
| CAD Export | ezdxf |

## Build Commands

### Frontend
```bash
cd frontend
npm install && npm run dev          # Start dev server (localhost:5173)
npm run typecheck && npm run lint && npm run test  # Pre-commit checks
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
docker-compose up -d postgres
alembic upgrade head                # Apply migrations
alembic revision --autogenerate -m "description"  # New migration
```

### ML Pipeline
```bash
cd ml
python training/train_symbol_detector.py  # Train CNN
python training/evaluate.py               # Evaluate model
```

## Project Structure

```
flowex/
├── frontend/           # React app (src/components, pages, hooks, lib, types)
├── backend/            # FastAPI app (app/api, core, models, services, ml)
├── ml/                 # Model training (data, models, training)
├── spec/               # Feature specifications (9 detailed spec files)
├── PRD.json            # Complete product requirements
├── IMPLEMENTATION_PLAN.md  # Task breakdown and progress
└── AGENTS.md           # Quick operational reference
```

## Architecture

**Data Flow:**
```
PDF Upload → Storage (Supabase/S3) → PDF Processing (Celery) → Symbol Detection (CNN) → OCR (Tesseract)
    ↓
Validation Interface (side-by-side) ← Human Review
    ↓
Export → AutoCAD DWG/DXF + Data Lists (Equipment, Line, Instrument, Valve, MTO)
```

**Key Patterns:**
- FastAPI async endpoints with SQLAlchemy ORM
- Background jobs via Celery + Redis for file processing
- JWT authentication (24h expiry, RS256)
- Organization-based multi-tenancy with RBAC
- ISO 10628 standard for P&ID symbols (50 classes)

## Development Workflow

This project uses the "Ralph" autonomous AI methodology:
1. One task per iteration
2. Tests must pass before committing
3. Follow existing code patterns
4. Update IMPLEMENTATION_PLAN.md after each task

## Key Files to Read First

1. **spec/*.md** - Detailed feature specifications
2. **IMPLEMENTATION_PLAN.md** - Current task queue and phase breakdown
3. **PRD.json** - Full product requirements and data models

## Known Pitfalls

- **PDF processing:** Large files need chunking via background jobs
- **OCR accuracy:** Pre-process scanned images (deskew, denoise, binarize)
- **File storage:** Always use EU region (eu-west-1) for GDPR
- **Auth tokens:** JWT expires in 24h; implement refresh logic

## Environment Variables

**Development (Supabase):**
```bash
STORAGE_PROVIDER=supabase
DATABASE_URL=postgresql://postgres.xxx:[password]@aws-0-eu-west-1.pooler.supabase.com:6543/postgres
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=xxx
SUPABASE_STORAGE_BUCKET=drawings
```

**Production (AWS):**
```bash
STORAGE_PROVIDER=aws
DATABASE_URL=postgresql://user:pass@localhost:5432/flowex
AWS_S3_BUCKET=flowex-uploads-eu
AWS_REGION=eu-west-1
AWS_ACCESS_KEY_ID=xxx
AWS_SECRET_ACCESS_KEY=xxx
```

**Common:**
```bash
AUTH0_DOMAIN=your-domain.auth0.com
AUTH0_CLIENT_ID=xxx
AUTH0_CLIENT_SECRET=xxx
REDIS_URL=redis://localhost:6379/0
```

See `docs/SUPABASE_SETUP.md` for detailed Supabase configuration.
