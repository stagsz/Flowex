# Flowex - AGENTS.md

Operational guide for building Flowex. Keep this file brief and actionable.

## Project Overview

Flowex is an AI-powered P&ID digitization platform. Convert PDF P&IDs to intelligent AutoCAD drawings + structured data lists.

**Target:** Mid-size EPCs (50-200 employees) in Waste-to-Energy/Environmental sectors (Europe).

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 18, TypeScript 5, Tailwind CSS, shadcn/ui, Zustand |
| Backend | Python 3.11, FastAPI, SQLAlchemy |
| Database | PostgreSQL 15 |
| AI/ML | PyTorch 2.x (CNN), Tesseract 5.x (OCR) |
| Storage | AWS S3 (EU region) |
| Auth | Auth0 (SSO: Microsoft, Google) |
| CAD Export | ezdxf |

## Directory Structure

```
flowex/
├── frontend/          # React application
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   ├── lib/       # Utilities
│   │   └── types/
│   └── tests/
├── backend/           # FastAPI application
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── models/
│   │   ├── services/
│   │   └── ml/        # AI/ML pipeline
│   └── tests/
├── ml/                # Model training
│   ├── data/
│   ├── models/
│   └── training/
└── specs/             # Requirement specifications
```

## Build Commands

### Frontend
```bash
cd frontend
npm install          # Install dependencies
npm run dev          # Development server (localhost:5173)
npm run build        # Production build
npm run typecheck    # TypeScript check
npm run lint         # ESLint
npm run test         # Vitest tests
npm run test:ui      # Vitest UI
```

### Backend
```bash
cd backend
pip install -r requirements.txt  # Install dependencies
uvicorn app.main:app --reload    # Dev server (localhost:8000)
pytest                           # Run tests
pytest --cov=app                 # With coverage
mypy app                         # Type checking
ruff check app                   # Linting
ruff format app                  # Formatting
```

### Database
```bash
# Using Docker
docker-compose up -d postgres

# Migrations (Alembic)
alembic upgrade head             # Apply migrations
alembic revision --autogenerate -m "description"  # New migration
```

### ML Pipeline
```bash
cd ml
python training/train_symbol_detector.py  # Train CNN
python training/evaluate.py               # Evaluate model
```

## Testing Strategy

1. **Unit tests** - Individual functions/components
2. **Integration tests** - API endpoints, database
3. **E2E tests** - Critical user flows (Playwright)
4. **ML tests** - Model accuracy benchmarks

Run all tests before committing:
```bash
# Frontend
cd frontend && npm run typecheck && npm run lint && npm run test

# Backend  
cd backend && mypy app && ruff check app && pytest
```

## Common Patterns

### API Endpoints (Backend)
```python
# app/api/routes/drawings.py
@router.post("/", response_model=DrawingResponse)
async def create_drawing(
    drawing: DrawingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await drawing_service.create(db, drawing, current_user)
```

### React Components (Frontend)
```typescript
// src/components/feature/ComponentName.tsx
interface Props { /* typed props */ }

export function ComponentName({ prop }: Props) {
  // hooks at top
  // handlers
  // render
}
```

## Known Pitfalls

1. **PDF processing** - Large files need chunking; use background jobs
2. **OCR accuracy** - Pre-process images (deskew, denoise) for scanned PDFs
3. **Symbol detection** - Ensure model trained on ISO 10628 symbols
4. **File storage** - Always use EU region for GDPR compliance
5. **Auth tokens** - JWT expiry is 24h; implement refresh logic

## Environment Variables

```bash
# Required
DATABASE_URL=postgresql://user:pass@localhost:5432/flowex
AUTH0_DOMAIN=your-domain.auth0.com
AUTH0_CLIENT_ID=xxx
AUTH0_CLIENT_SECRET=xxx
AWS_S3_BUCKET=flowex-uploads-eu
AWS_REGION=eu-west-1

# Optional
SENTRY_DSN=xxx
LOG_LEVEL=INFO
```

## Useful Commands

```bash
# Git
git status
git diff --staged
git log --oneline -10

# Docker
docker-compose up -d      # Start services
docker-compose logs -f    # View logs
docker-compose down       # Stop services

# Quick checks
curl http://localhost:8000/health  # Backend health
```

---

*Last updated by Ralph. Keep this file under 60 lines of operational content.*