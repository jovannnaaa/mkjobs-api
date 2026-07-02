from dataclasses import dataclass

from fastapi import Query


@dataclass
class PaginationParams:
    cursor: str | None
    page_size: int


def pagination_params(
    cursor: str | None = Query(default=None, description="Opaque cursor from previous response"),
    pageSize: int = Query(default=10, ge=1, le=100),
) -> PaginationParams:
    return PaginationParams(cursor=cursor, page_size=pageSize)
