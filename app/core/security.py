"""Lightweight security helpers: request IDs and in-memory rate limiting.

This is a public read-only API (see README), so there is no auth layer here
by design. Rate limiting is a simple fixed-window counter per client IP,
sufficient for a single-instance deployment behind the reverse proxy.
"""
import time
import uuid
from collections import defaultdict

from fastapi import Request
from starlette.responses import JSONResponse

from app.core.config import get_settings

_WINDOW_SECONDS = 60
_hits: dict[str, list[float]] = defaultdict(list)


def new_request_id() -> str:
    return uuid.uuid4().hex


def is_rate_limited(client_key: str) -> bool:
    settings = get_settings()
    now = time.time()
    window_start = now - _WINDOW_SECONDS
    hits = [t for t in _hits[client_key] if t > window_start]
    hits.append(now)
    _hits[client_key] = hits
    return len(hits) > settings.rate_limit_per_minute


async def rate_limit_middleware(request: Request, call_next):
    client_key = request.client.host if request.client else "unknown"
    if is_rate_limited(client_key):
        return JSONResponse(
            status_code=429,
            content={"error": "rate_limited", "message": "Too many requests"},
        )
    return await call_next(request)
