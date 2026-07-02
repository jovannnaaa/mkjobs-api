"""Celery Beat schedule for the 'cv_mk' source."""
from celery.schedules import crontab

SCHEDULE = {
    "schedule": crontab(minute=15, hour="*/1"),  # hourly at :15
    "options": {"queue": "scraping"},
}
