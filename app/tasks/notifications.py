from celery import shared_task

from app.webhooks.dispatch import dispatch_webhooks


@shared_task(name="tasks.notify_new_postings")
def notify_new_postings(postings: list[dict]) -> None:
    dispatch_webhooks("posting.new", postings)


@shared_task(name="tasks.notify_closed_postings")
def notify_closed_postings(postings: list[dict]) -> None:
    dispatch_webhooks("posting.closed", postings)


@shared_task(name="tasks.notify_posting_changed")
def notify_posting_changed(postings: list[dict]) -> None:
    dispatch_webhooks("posting.changed", postings)
