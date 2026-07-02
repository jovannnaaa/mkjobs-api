"""Celery application: worker + beat entry point.

Run as a worker:
    celery -A app.worker worker --loglevel=info

Run as the beat scheduler:
    celery -A app.worker beat --loglevel=info
"""
from celery import Celery

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.sources.registry import SCHEDULES

configure_logging()
settings = get_settings()

celery_app = Celery(
    "mkjobs",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.scraping", "app.tasks.notifications"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_default_queue="default",
    task_routes={
        "tasks.scrape_source": {"queue": "scraping"},
        "tasks.notify_*": {"queue": "notifications"},
    },
)

# Build the beat schedule from each source's own schedule.py, so adding a new
# portal under app/sources/<portal>/ automatically wires up its cron entry.
celery_app.conf.beat_schedule = {
    f"scrape-{slug}": {
        "task": "tasks.scrape_source",
        "schedule": schedule["schedule"],
        "args": (slug,),
        "options": schedule.get("options", {}),
    }
    for slug, schedule in SCHEDULES.items()
}
