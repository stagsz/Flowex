import traceback
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.routes import auth, cloud, drawings, exports, feedback, projects, users
from app.core.config import settings
from app.core.logging import (
    generate_request_id,
    get_logger,
    set_request_id,
    setup_logging,
)
from app.core.rate_limiting import get_limiter
from app.core.security_headers import SecurityHeadersMiddleware

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

    sentry_sdk.init(  # type: ignore[call-arg]
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

# Configure rate limiting
limiter = get_limiter()
app.state.limiter = limiter


async def rate_limit_exceeded_handler(request: Request, exc: Exception) -> Response:
    """Handle rate limit exceeded errors with CORS headers."""
    # Cast to RateLimitExceeded for type safety
    rate_exc = exc if isinstance(exc, RateLimitExceeded) else None
    detail = str(rate_exc.detail) if rate_exc else "Rate limit exceeded"

    # Add CORS headers for rate limit responses
    origin = request.headers.get("origin")
    headers: dict[str, str] = {}
    if origin and origin in settings.CORS_ORIGINS:
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Credentials"] = "true"

    return JSONResponse(
        status_code=429,
        content={"error": "rate_limit_exceeded", "detail": detail},
        headers=headers,
    )


app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)


# Global exception handler to ensure CORS headers on errors
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle all uncaught exceptions and ensure CORS headers are present."""
    # Log the full error
    logger.error(f"Unhandled exception: {exc}\n{traceback.format_exc()}")

    # Return error with CORS headers
    origin = request.headers.get("origin")
    headers = {}
    if origin and origin in settings.CORS_ORIGINS:
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Credentials"] = "true"

    return JSONResponse(
        status_code=500,
        content={"detail": str(exc) if settings.DEBUG else "Internal server error"},
        headers=headers,
    )


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware to add request correlation IDs for log tracing."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
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

# Add security headers middleware (after request ID, before CORS)
app.add_middleware(SecurityHeadersMiddleware)

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
app.include_router(users.router, prefix="/api/v1")
app.include_router(feedback.router, prefix="/api/v1")


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "healthy", "version": "0.1.0"}


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Flowex API", "docs": "/docs"}
