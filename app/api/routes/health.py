from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import check_db_connection, get_db
from app.core.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/ping")
async def ping():
    return {"status": "ok"}


@router.get("/ready")
async def ready(db: AsyncSession = Depends(get_db)):
    db_ok = await check_db_connection()

    redis_ok = True
    try:
        import redis.asyncio as aioredis

        settings = get_settings()
        client = aioredis.from_url(settings.redis_url)
        await client.ping()
        await client.aclose()
    except Exception:  # noqa: BLE001
        redis_ok = False

    status_code_ok = db_ok and redis_ok
    return {
        "status": "ok" if status_code_ok else "degraded",
        "checks": {"database": db_ok, "redis": redis_ok},
    }
