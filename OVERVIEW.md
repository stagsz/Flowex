## Flowex - P&ID Digitization Platform

**What it does:** Converts legacy PDF P&ID (Piping & Instrumentation Diagrams) into editable AutoCAD drawings (DWG/DXF) and structured engineering data using AI.

### Key Features

- **PDF Upload & Processing** - Upload scanned P&ID documents for automated analysis
- **AI Symbol Detection** - CNN-based recognition of 50+ ISO 10628 standard symbols (valves, instruments, equipment)
- **OCR Extraction** - Tesseract-powered text recognition for labels, tags, and annotations
- **Human Validation** - Side-by-side review interface for accuracy verification
- **CAD Export** - Generate editable DWG/DXF files from processed diagrams
- **Data Lists Export** - Extract structured lists:
  - Equipment lists
  - Line lists
  - Instrument lists
  - Valve lists
  - MTO (Material Take-Off)

### Tech Highlights

| Area | Stack |
|------|-------|
| Frontend | React, TypeScript, Tailwind |
| Backend | Python, FastAPI |
| AI/ML | PyTorch (ResNet-50), Tesseract OCR |
| Auth | Auth0 SSO (Microsoft/Google) |
| Storage | AWS S3 |

**Status:** Planning phase complete, implementation in progress.
