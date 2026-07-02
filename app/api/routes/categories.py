from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import PaginationParams, pagination_params
from app.common.schemas import CategoryOut, Envelope, PageMeta, PostingOut
from app.core.db import get_db
from app.models import Category, Posting

router = APIRouter(tags=["categories"])


@router.get("/categories", response_model=list[CategoryOut])
async def list_categories(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Category).order_by(Category.name.asc()))
    return result.scalars().all()


@router.get("/categories/{category_id}/postings", response_model=Envelope[PostingOut])
async def get_category_postings(
    category_id: int,
    pagination: PaginationParams = Depends(pagination_params),
    sortDirection: Literal["asc", "desc"] = Query(default="desc"),
    db: AsyncSession = Depends(get_db),
):
    from app.api.routes.postings import _paginated_postings, _base_query

    exists = await db.execute(select(Category.id).where(Category.id == category_id))
    if exists.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Category not found")

    query = _base_query().where(Posting.category_id == category_id)
    rows, next_cursor, has_more = await _paginated_postings(db, query, "postedAt", sortDirection, pagination)

    return Envelope(
        data=[PostingOut.from_orm_obj(p) for p in rows],
        meta=PageMeta(nextCursor=next_cursor, pageSize=pagination.page_size, hasMore=has_more),
    )
