# Flowex Performance Testing

This directory contains performance testing infrastructure for the Flowex platform.

## Overview

Performance testing covers three main areas:

1. **API Load Testing** (k6) - Tests backend API endpoints under load
2. **Frontend Performance** (Lighthouse CI) - Measures Core Web Vitals
3. **Backend Benchmarks** (pytest-benchmark) - Profiles critical code paths

## Quick Start

### Prerequisites

```bash
# Install k6
# macOS
brew install k6

# Windows (with Chocolatey)
choco install k6

# Linux
sudo gpg -k
sudo gpg --no-default-keyring --keyring /usr/share/keyrings/k6-archive-keyring.gpg --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list
sudo apt-get update
sudo apt-get install k6
```

### Running k6 Load Tests

```bash
# Smoke test (default)
k6 run perf/k6/api-endpoints.js

# Load test
k6 run -e PROFILE=load perf/k6/api-endpoints.js

# Stress test
k6 run -e PROFILE=stress perf/k6/api-endpoints.js

# Upload stress test (10 concurrent uploads)
k6 run perf/k6/upload-stress.js

# With custom base URL
k6 run -e BASE_URL=https://staging.flowex.io perf/k6/api-endpoints.js
```

### Running Backend Benchmarks

```bash
cd backend

# Install benchmark dependency
pip install pytest-benchmark

# Run all benchmarks
pytest tests/test_benchmarks.py -v

# Run with JSON output
pytest tests/test_benchmarks.py -v --benchmark-json=benchmark-results.json

# Run specific benchmark group
pytest tests/test_benchmarks.py -v -k "PDFProcessing"
```

### Running Lighthouse CI

```bash
cd frontend

# Install Lighthouse CI
npm install -g @lhci/cli

# Run against dev server
lhci autorun

# Run with custom config
lhci autorun --config=lighthouserc.js
```

## Test Profiles

### k6 Profiles

| Profile | VUs | Duration | Use Case |
|---------|-----|----------|----------|
| smoke | 1 | 30s | Verify tests work |
| load | 10 | 5m | Normal expected load |
| stress | 50 | 20m | Find breaking point |
| spike | 50 | 3m | Sudden load increase |
| soak | 10 | 30m+ | Extended duration |

### Lighthouse Assertions

| Metric | Target | Spec Reference |
|--------|--------|----------------|
| LCP | < 3000ms | Initial load < 3s |
| FCP | < 2000ms | First paint target |
| TBT | < 300ms | Responsiveness |
| CLS | < 0.1 | Layout stability |
| Performance Score | > 80 | Overall target |

## Performance Targets (from Spec)

### Backend API

- Health check: < 100ms (p95)
- Drawing list: < 500ms (p95)
- Drawing get: < 300ms (p95)
- Export status: < 200ms (p95)
- File upload: < 30s for small files
- Concurrent uploads: 10 simultaneous

### Processing Pipeline

- PDF type detection: < 100ms
- Image preprocessing: < 500ms (1024x1024)
- Tile creation: < 200ms (2048x2048)
- Full P&ID processing: < 60s

### Frontend

- Initial load: < 3s
- Edit feedback: < 100ms
- Pan/zoom: 60 FPS

## CI Integration

Performance tests run automatically via GitHub Actions:

- **On PR**: Lighthouse CI runs
- **On push to master**: Full suite runs
- **Manual trigger**: Choose k6 profile

See `.github/workflows/performance.yml` for configuration.

## Results

Test results are stored in:
- `perf/k6/results/` - k6 JSON summaries
- `backend/benchmark-results.json` - pytest-benchmark output
- Lighthouse reports uploaded to temporary public storage

## Troubleshooting

### k6 tests fail to connect

1. Ensure backend is running: `uvicorn app.main:app --reload`
2. Check BASE_URL environment variable
3. Verify auth token if testing protected endpoints

### Lighthouse times out

1. Increase `startServerReadyTimeout` in lighthouserc.js
2. Ensure frontend builds successfully: `npm run build`
3. Check for console errors in dev tools

### Benchmarks are slow

1. Run with fewer iterations: `pytest --benchmark-min-rounds=1`
2. Skip database tests: `pytest -k "not database"`
3. Use smaller test data
