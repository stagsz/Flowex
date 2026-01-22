import ssl

from celery import Celery

from app.core.config import settings

# Dev/eager mode: run tasks synchronously without Redis/Celery worker
# Set CELERY_TASK_ALWAYS_EAGER=true to enable
if settings.CELERY_TASK_ALWAYS_EAGER:
    # Don't connect to Redis in eager mode - use memory backend
    celery_app = Celery(
        "flowex",
        broker="memory://",
        backend="cache+memory://",
        include=["app.tasks.processing"],
    )
    celery_app.conf.update(
        task_always_eager=True,
        task_eager_propagates=True,
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
    )
else:
    # Production mode: use Redis
    celery_app = Celery(
        "flowex",
        broker=settings.REDIS_URL,
        backend=settings.REDIS_URL,
        include=["app.tasks.processing"],
    )

    # Base configuration
    celery_app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_time_limit=600,  # 10 minutes max per task
        task_soft_time_limit=540,  # 9 minutes soft limit
        worker_prefetch_multiplier=1,  # Process one task at a time
        task_acks_late=True,  # Acknowledge after task completes
        task_reject_on_worker_lost=True,
    )

    # SSL configuration for rediss:// URLs (e.g., Upstash)
    if settings.REDIS_URL.startswith("rediss://"):
        celery_app.conf.update(
            broker_use_ssl={"ssl_cert_reqs": ssl.CERT_REQUIRED},
            redis_backend_use_ssl={"ssl_cert_reqs": ssl.CERT_REQUIRED},
        )
