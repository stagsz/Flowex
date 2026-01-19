from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.routes import auth, cloud, drawings, exports, projects
from app.core.config import settings
from app.core.logging import (
    generate_request_id,
    get_logger,
    set_request_id,
    setup_logging,
)

# Configure logging before anything else
setup_logging(
    debug=settings.DEBUG,
    json_logs=settings.LOG_JSON_FORMAT,
)

logger = get_logger(__name__)

# Initialize Sentry for error tracking and performance monitoring
if settings.SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.redis import RedisIntegration
    from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.SENTRY_ENVIRONMENT,
        traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
        profiles_sample_rate=settings.SENTRY_PROFILES_SAMPLE_RATE,
        integrations=[
            FastApiIntegration(transaction_style="endpoint"),
            SqlalchemyIntegration(),
            CeleryIntegration(),
            RedisIntegration(),
        ],
        # Don't send PII
        send_default_pii=False,
        # Attach request data for debugging
        request_bodies="medium",
        # Filter out health check transactions
        traces_sampler=lambda ctx: 0 if ctx.get("transaction_context", {}).get("name") == "/health" else settings.SENTRY_TRACES_SAMPLE_RATE,
    )

app = FastAPI(
    title="Flowex API",
    description="AI-Powered P&ID Digitization Platform",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware to add request correlation IDs for log tracing."""

    async def dispatch(self, request: Request, call_next):
        """Add request ID to context and response headers."""
        # Check for existing request ID from load balancer or generate new one
        request_id = request.headers.get("X-Request-ID") or generate_request_id()
        set_request_id(request_id)

        # Log request start
        logger.info(
            f"Request started: {request.method} {request.url.path}",
        )

        response = await call_next(request)

        # Add request ID to response headers for client correlation
        response.headers["X-Request-ID"] = request_id

        # Log request completion
        logger.info(
            f"Request completed: {request.method} {request.url.path} - {response.status_code}",
        )

        return response


# Add request ID middleware first (before CORS)
app.add_middleware(RequestIDMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(projects.router, prefix="/api/v1")
app.include_router(drawings.router, prefix="/api/v1")
app.include_router(exports.router, prefix="/api/v1")
app.include_router(cloud.router, prefix="/api/v1")


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "healthy", "version": "0.1.0"}


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Flowex API", "docs": "/docs"}
