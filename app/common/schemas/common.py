from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PageMeta(BaseModel):
    nextCursor: str | None = None
    pageSize: int
    hasMore: bool


class Envelope(BaseModel, Generic[T]):
    data: list[T]
    meta: PageMeta


class ErrorResponse(BaseModel):
    error: str
    message: str
