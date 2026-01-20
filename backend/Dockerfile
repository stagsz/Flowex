# Backend Dockerfile - Multi-stage build for Flowex API
# Python 3.11 with Tesseract OCR and PyTorch

# Stage 1: Builder
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies (use prod file for smaller image)
COPY requirements-prod.txt .
RUN pip wheel --no-cache-dir --wheel-dir /app/wheels -r requirements-prod.txt

# Stage 2: Runtime
FROM python:3.11-slim as runtime

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    # Tesseract data path
    TESSDATA_PREFIX=/usr/share/tesseract-ocr/5/tessdata

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    # PostgreSQL client
    libpq5 \
    # Tesseract OCR
    tesseract-ocr \
    tesseract-ocr-eng \
    # PDF processing (poppler for pdf2image)
    poppler-utils \
    # Image processing
    libmagic1 \
    # Health check
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy wheels and install
COPY --from=builder /app/wheels /wheels
RUN pip install --no-cache /wheels/* \
    && rm -rf /wheels

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser \
    && mkdir -p /app/uploads /app/exports \
    && chown -R appuser:appuser /app

# Copy application code
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

# Expose port (Railway sets PORT dynamically)
EXPOSE 8000

# Note: Railway uses its own healthcheck, Docker HEALTHCHECK is ignored
# HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
#     CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Default command - Railway overrides this with startCommand from railway.json
# Use shell form to expand $PORT environment variable
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1
