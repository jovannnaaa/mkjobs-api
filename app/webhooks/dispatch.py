"""Webhook URL collection (by numbered env prefix) and dispatch."""
import os
from datetime import datetime, timezone

import httpx
import structlog

logger = structlog.get_logger("mkjobs.webhooks")

PREFIXES = {
    "posting.new": "NEW_POSTINGS_WEBHOOK_",
    "posting.closed": "CLOSED_POSTINGS_WEBHOOK_",
    "posting.changed": "POSTING_CHANGED_WEBHOOK_",
}


def collect_webhook_urls(event: str) -> list[str]:
    prefix = PREFIXES.get(event)
    if not prefix:
        return []
    urls = []
    for key, value in os.environ.items():
        if key.startswith(prefix) and value:
            urls.append(value)
    return urls


def dispatch_webhooks(event: str, data: list[dict]) -> None:
    urls = collect_webhook_urls(event)
    if not urls:
        logger.info("webhook_skip_no_endpoints", event=event)
        return

    payload = {
        "data": data,
        "meta": {
            "event": event,
            "dispatchedAt": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
        },
    }

    with httpx.Client(timeout=10.0) as client:
        for url in urls:
            try:
                response = client.post(url, json=payload)
                response.raise_for_status()
                logger.info("webhook_dispatched", event=event, url=url, status=response.status_code)
            except Exception as exc:  # noqa: BLE001
                logger.error("webhook_dispatch_failed", event=event, url=url, error=str(exc))
