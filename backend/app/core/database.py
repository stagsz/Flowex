from collections.abc import AsyncGenerator, Generator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


def _get_engine_kwargs() -> dict:
    """Get engine configuration based on database type."""
    kwargs = {
        "pool_pre_ping": True,
        "pool_size": 10,
        "max_overflow": 20,
    }

    # Supabase pooler connections (port 6543) work in transaction mode
    # and require specific settings
    if "pooler.supabase.com" in settings.DATABASE_URL:
        kwargs.update({
            "pool_size": 5,  # Smaller pool for Supabase free tier
            "max_overflow": 10,
            "pool_timeout": 30,
            "pool_recycle": 1800,  # Recycle connections every 30 mins
        })

    return kwargs


def _get_async_database_url() -> str:
    """Convert sync database URL to async version."""
    url = settings.DATABASE_URL
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


# Synchronous engine and session (existing)
engine = create_engine(settings.DATABASE_URL, **_get_engine_kwargs())
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Asynchronous engine and session (new for cloud storage)
async_engine = create_async_engine(_get_async_database_url(), **_get_engine_kwargs())
AsyncSessionLocal = async_sessionmaker(
    async_engine, class_=AsyncSession, expire_on_commit=False
)


def get_db() -> Generator[Session, None, None]:
    """Dependency to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get async database session."""
    async with AsyncSessionLocal() as session:
        yield session
