# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Flowex is an AI-powered P&ID (Piping & Instrumentation Diagram) digitization platform. It converts legacy PDF P&IDs into editable AutoCAD drawings (DWG/DXF) and structured engineering data lists using computer vision and OCR.

**Status:** Planning phase - specifications complete, no production code yet.

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 18, TypeScript 5, Tailwind CSS, shadcn/ui, Zustand, Vitest |
| Backend | Python 3.11, FastAPI, SQLAlchemy, pytest |
| Database | PostgreSQL 15, Redis (cache) |
| AI/ML | PyTorch 2.x (ResNet-50 + FPN), Tesseract 5.x (OCR) |
| Storage | AWS S3 (eu-west-1) |
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
PDF Upload → S3 Storage → PDF Processing (Celery) → Symbol Detection (CNN) → OCR (Tesseract)
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

```bash
DATABASE_URL=postgresql://user:pass@localhost:5432/flowex
AUTH0_DOMAIN=your-domain.auth0.com
AUTH0_CLIENT_ID=xxx
AUTH0_CLIENT_SECRET=xxx
AWS_S3_BUCKET=flowex-uploads-eu
AWS_REGION=eu-west-1
```
