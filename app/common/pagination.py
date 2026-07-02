"""Opaque cursor encoding/decoding for keyset pagination.

The cursor encodes the sort field, sort direction, and the value/id of the
last row seen, so the API can resume via `WHERE (sort_col, id) > (val, id)`
style comparisons instead of relying on OFFSET.
"""
import base64
import json
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException


class InvalidCursorError(HTTPException):
    def __init__(self):
        super().__init__(status_code=400, detail="Invalid cursor")


@dataclass
class Cursor:
    sort_by: str
    sort_direction: str
    value: Any
    id: int


def encode_cursor(cursor: Cursor) -> str:
    payload = {
        "sortBy": cursor.sort_by,
        "sortDirection": cursor.sort_direction,
        "value": cursor.value,
        "id": cursor.id,
    }
    raw = json.dumps(payload, default=str).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii")


def decode_cursor(token: str, expected_sort_by: str, expected_sort_direction: str) -> Cursor:
    try:
        raw = base64.urlsafe_b64decode(token.encode("ascii"))
        payload = json.loads(raw)
        cursor = Cursor(
            sort_by=payload["sortBy"],
            sort_direction=payload["sortDirection"],
            value=payload["value"],
            id=int(payload["id"]),
        )
    except Exception as exc:  # noqa: BLE001
        raise InvalidCursorError() from exc

    if cursor.sort_by != expected_sort_by or cursor.sort_direction != expected_sort_direction:
        raise InvalidCursorError()

    return cursor


def clamp_page_size(page_size: int, default: int = 10, minimum: int = 1, maximum: int = 100) -> int:
    if page_size is None:
        return default
    return max(minimum, min(maximum, page_size))
