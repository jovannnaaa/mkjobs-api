"""Celery Beat schedule for the 'vrabotuvanje' source."""
from celery.schedules import crontab

SCHEDULE = {
    "schedule": crontab(minute="*/30"),  # every 30 minutes
    "options": {"queue": "scraping"},
}
