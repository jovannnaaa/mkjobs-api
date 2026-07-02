"""SQLAlchemy engine / session management.

Two engines are exposed:
- `engine` / `AsyncSessionLocal`: async, used by the FastAPI process.
- `sync_engine` / `SyncSessionLocal`: sync (psycopg2), used by Celery tasks,
  since Celery workers are synchronous by nature and mixing asyncio event
  loops into task execution adds needless complexity.
"""
from collections.abc import AsyncGenerator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.resolved_database_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=10,
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


def _sync_url(url: str) -> str:
    return url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")


sync_engine = create_engine(
    _sync_url(settings.resolved_database_url),
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=5,
    future=True,
)

SyncSessionLocal = sessionmaker(bind=sync_engine, expire_on_commit=False, autoflush=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def check_db_connection() -> bool:
    from sqlalchemy import text

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
