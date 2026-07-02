from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models import Employer, Posting, Source

router = APIRouter(tags=["stats"])


@router.get("/stats")
async def stats(db: AsyncSession = Depends(get_db)):
    total_postings = (await db.execute(select(func.count(Posting.id)))) .scalar_one()
    active_postings = (
        await db.execute(select(func.count(Posting.id)).where(Posting.is_active.is_(True)))
    ).scalar_one()
    total_employers = (await db.execute(select(func.count(Employer.id)))).scalar_one()
    total_sources = (
        await db.execute(select(func.count(Source.id)).where(Source.is_active.is_(True)))
    ).scalar_one()

    return {
        "postings": {"total": total_postings, "active": active_postings},
        "employers": {"total": total_employers},
        "sources": {"active": total_sources},
    }
