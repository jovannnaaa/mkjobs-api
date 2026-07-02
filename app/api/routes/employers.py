from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.api.dependencies import PaginationParams, pagination_params
from app.common.pagination import Cursor, decode_cursor, encode_cursor
from app.common.schemas import Envelope, EmployerOut, PageMeta, PostingOut
from app.core.db import get_db
from app.models import Employer, Posting

router = APIRouter(tags=["employers"])

SORTABLE_COLUMNS = {
    "id": Employer.id,
}


@router.get("/employers", response_model=Envelope[EmployerOut])
async def list_employers(
    pagination: PaginationParams = Depends(pagination_params),
    sortBy: str = Query(default="id"),
    sortDirection: Literal["asc", "desc"] = Query(default="asc"),
    db: AsyncSession = Depends(get_db),
):
    # activePostingsCount / totalPostingsCount are computed via subqueries when requested
    if sortBy == "id":
        query = select(Employer)
        descending = sortDirection == "desc"
        if pagination.cursor:
            cursor = decode_cursor(pagination.cursor, "id", sortDirection)
            if descending:
                query = query.where(Employer.id < cursor.id)
            else:
                query = query.where(Employer.id > cursor.id)
        query = query.order_by(Employer.id.desc() if descending else Employer.id.asc())
        query = query.limit(pagination.page_size + 1)
        result = await db.execute(query)
        rows = result.scalars().all()
    elif sortBy in ("activePostingsCount", "totalPostingsCount"):
        active_only = sortBy == "activePostingsCount"
        count_expr = func.count(Posting.id)
        query = (
            select(Employer, count_expr.label("posting_count"))
            .outerjoin(
                Posting,
                and_(Posting.employer_id == Employer.id, Posting.is_active.is_(True))
                if active_only
                else Posting.employer_id == Employer.id,
            )
            .group_by(Employer.id)
        )
        descending = sortDirection == "desc"
        if pagination.cursor:
            cursor = decode_cursor(pagination.cursor, sortBy, sortDirection)
            if descending:
                query = query.having(
                    or_(count_expr < cursor.value, and_(count_expr == cursor.value, Employer.id < cursor.id))
                )
            else:
                query = query.having(
                    or_(count_expr > cursor.value, and_(count_expr == cursor.value, Employer.id > cursor.id))
                )
        order_col = count_expr.desc() if descending else count_expr.asc()
        order_id = Employer.id.desc() if descending else Employer.id.asc()
        query = query.order_by(order_col, order_id).limit(pagination.page_size + 1)
        result = await db.execute(query)
        pairs = result.all()
        rows = [p[0] for p in pairs]
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported sortBy '{sortBy}'")

    has_more = len(rows) > pagination.page_size
    rows = rows[: pagination.page_size]

    next_cursor = None
    if has_more and rows:
        last = rows[-1]
        if sortBy == "id":
            value = last.id
        else:
            # recompute the count for the last row to encode into the cursor
            active_only = sortBy == "activePostingsCount"
            count_query = select(func.count(Posting.id)).where(Posting.employer_id == last.id)
            if active_only:
                count_query = count_query.where(Posting.is_active.is_(True))
            value = (await db.execute(count_query)).scalar_one()
        next_cursor = encode_cursor(Cursor(sort_by=sortBy, sort_direction=sortDirection, value=value, id=last.id))

    return Envelope(
        data=[EmployerOut.from_orm_aliased(e) for e in rows],
        meta=PageMeta(nextCursor=next_cursor, pageSize=pagination.page_size, hasMore=has_more),
    )


@router.get("/employers/{employer_id}", response_model=EmployerOut)
async def get_employer(employer_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Employer).where(Employer.id == employer_id))
    employer = result.scalar_one_or_none()
    if employer is None:
        raise HTTPException(status_code=404, detail="Employer not found")
    return EmployerOut.from_orm_aliased(employer)


@router.get("/employers/{employer_id}/postings", response_model=Envelope[PostingOut])
async def get_employer_postings(
    employer_id: int,
    pagination: PaginationParams = Depends(pagination_params),
    sortDirection: Literal["asc", "desc"] = Query(default="desc"),
    db: AsyncSession = Depends(get_db),
):
    from app.api.routes.postings import _paginated_postings, _base_query

    exists = await db.execute(select(Employer.id).where(Employer.id == employer_id))
    if exists.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Employer not found")

    query = _base_query().where(Posting.employer_id == employer_id)
    rows, next_cursor, has_more = await _paginated_postings(db, query, "postedAt", sortDirection, pagination)

    return Envelope(
        data=[PostingOut.from_orm_obj(p) for p in rows],
        meta=PageMeta(nextCursor=next_cursor, pageSize=pagination.page_size, hasMore=has_more),
    )
