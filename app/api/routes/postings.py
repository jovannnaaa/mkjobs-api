from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Numeric, and_, cast, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.api.dependencies import PaginationParams, pagination_params
from app.common.enums import EmploymentType, SeniorityLevel
from app.common.pagination import Cursor, decode_cursor, encode_cursor
from app.common.schemas import Envelope, PageMeta, PostingHistoryOut, PostingOut
from app.core.db import get_db
from app.models import Category, Employer, Posting, PostingHistory, Source

router = APIRouter(tags=["postings"])

SORTABLE_COLUMNS = {
    "postedAt": Posting.posted_at,
    "closingAt": Posting.closing_at,
    "salaryEstimate": Posting.salary_min,
}


def _base_query():
    return select(Posting).options(
        joinedload(Posting.employer),
        joinedload(Posting.category),
        joinedload(Posting.source),
    )


async def _paginated_postings(
    db: AsyncSession,
    query,
    sort_by: str,
    sort_direction: Literal["asc", "desc"],
    pagination: PaginationParams,
):
    if sort_by not in SORTABLE_COLUMNS:
        raise HTTPException(status_code=400, detail=f"Unsupported sortBy '{sort_by}'")

    column = SORTABLE_COLUMNS[sort_by]
    descending = sort_direction == "desc"

    if pagination.cursor:
        cursor = decode_cursor(pagination.cursor, sort_by, sort_direction)
        cmp_value = cursor.value
        if descending:
            query = query.where(
                or_(
                    column < cmp_value,
                    and_(column == cmp_value, Posting.id < cursor.id),
                )
            )
        else:
            query = query.where(
                or_(
                    column > cmp_value,
                    and_(column == cmp_value, Posting.id > cursor.id),
                )
            )

    order_col = column.desc() if descending else column.asc()
    order_id = Posting.id.desc() if descending else Posting.id.asc()
    query = query.order_by(order_col, order_id).limit(pagination.page_size + 1)

    result = await db.execute(query)
    rows = result.unique().scalars().all()

    has_more = len(rows) > pagination.page_size
    rows = rows[: pagination.page_size]

    next_cursor = None
    if has_more and rows:
        last = rows[-1]
        value = getattr(last, {"postedAt": "posted_at", "closingAt": "closing_at", "salaryEstimate": "salary_min"}[sort_by])
        if value is not None and sort_by == "salaryEstimate":
            value = float(value)
        next_cursor = encode_cursor(Cursor(sort_by=sort_by, sort_direction=sort_direction, value=value, id=last.id))

    return rows, next_cursor, has_more


@router.get("/postings", response_model=Envelope[PostingOut])
async def list_postings(
    pagination: PaginationParams = Depends(pagination_params),
    sortBy: str = Query(default="postedAt"),
    sortDirection: Literal["asc", "desc"] = Query(default="desc"),
    category: str | None = Query(default=None, description="Category slug"),
    seniority: SeniorityLevel | None = Query(default=None),
    employmentType: EmploymentType | None = Query(default=None),
    location: str | None = Query(default=None),
    isActive: bool | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    query = _base_query()

    if category:
        query = query.join(Category, Posting.category_id == Category.id).where(Category.slug == category)
    if seniority:
        query = query.where(Posting.seniority == seniority)
    if employmentType:
        query = query.where(Posting.employment_type == employmentType)
    if location:
        query = query.where(Posting.location.ilike(f"%{location}%"))
    if isActive is not None:
        query = query.where(Posting.is_active.is_(isActive))

    rows, next_cursor, has_more = await _paginated_postings(db, query, sortBy, sortDirection, pagination)

    return Envelope(
        data=[PostingOut.from_orm_obj(p) for p in rows],
        meta=PageMeta(nextCursor=next_cursor, pageSize=pagination.page_size, hasMore=has_more),
    )


@router.get("/postings/{posting_id}", response_model=PostingOut)
async def get_posting(posting_id: int, db: AsyncSession = Depends(get_db)):
    query = _base_query().where(Posting.id == posting_id)
    result = await db.execute(query)
    posting = result.unique().scalar_one_or_none()
    if posting is None:
        raise HTTPException(status_code=404, detail="Posting not found")
    return PostingOut.from_orm_obj(posting)


@router.get("/postings/{posting_id}/history", response_model=Envelope[PostingHistoryOut])
async def get_posting_history(
    posting_id: int,
    pagination: PaginationParams = Depends(pagination_params),
    sortDirection: Literal["asc", "desc"] = Query(default="desc"),
    db: AsyncSession = Depends(get_db),
):
    exists = await db.execute(select(Posting.id).where(Posting.id == posting_id))
    if exists.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Posting not found")

    descending = sortDirection == "desc"
    query = select(PostingHistory).where(PostingHistory.posting_id == posting_id)

    if pagination.cursor:
        cursor = decode_cursor(pagination.cursor, "changedAt", sortDirection)
        cmp_value = datetime.fromisoformat(cursor.value) if isinstance(cursor.value, str) else cursor.value
        if descending:
            query = query.where(
                or_(
                    PostingHistory.changed_at < cmp_value,
                    and_(PostingHistory.changed_at == cmp_value, PostingHistory.id < cursor.id),
                )
            )
        else:
            query = query.where(
                or_(
                    PostingHistory.changed_at > cmp_value,
                    and_(PostingHistory.changed_at == cmp_value, PostingHistory.id > cursor.id),
                )
            )

    order_col = PostingHistory.changed_at.desc() if descending else PostingHistory.changed_at.asc()
    order_id = PostingHistory.id.desc() if descending else PostingHistory.id.asc()
    query = query.order_by(order_col, order_id).limit(pagination.page_size + 1)

    result = await db.execute(query)
    rows = result.scalars().all()

    has_more = len(rows) > pagination.page_size
    rows = rows[: pagination.page_size]

    next_cursor = None
    if has_more and rows:
        last = rows[-1]
        next_cursor = encode_cursor(
            Cursor(sort_by="changedAt", sort_direction=sortDirection, value=last.changed_at, id=last.id)
        )

    return Envelope(
        data=[PostingHistoryOut.from_orm_obj(h) for h in rows],
        meta=PageMeta(nextCursor=next_cursor, pageSize=pagination.page_size, hasMore=has_more),
    )
