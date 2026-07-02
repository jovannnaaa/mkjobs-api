"""Celery tasks: run a source's scraper, dedupe/normalize, upsert postings,
record history, and fan out notifications for new/changed/closed postings.
"""
import asyncio

from celery import shared_task
from sqlalchemy import select

from app.core.db import SyncSessionLocal
from app.core.logging import get_logger
from app.models import Category, Employer, Posting, PostingHistory, Source
from app.sources.base import NormalizedPosting
from app.sources.registry import get_scraper
from app.tasks.dedup import content_hash, is_duplicate

logger = get_logger("mkjobs.tasks.scraping")

TRACKED_FIELDS = ["title", "location", "salary_min", "salary_max", "closing_at", "is_active"]


def _get_or_create_employer(db, name: str) -> Employer:
    from app.tasks.dedup import normalize_text

    normalized = normalize_text(name)
    employer = db.execute(select(Employer).where(Employer.normalized_name == normalized)).scalar_one_or_none()
    if employer:
        return employer
    employer = Employer(name=name, normalized_name=normalized)
    db.add(employer)
    db.flush()
    return employer


def _get_or_create_category(db, slug: str | None, name: str | None) -> Category | None:
    if not slug:
        return None
    category = db.execute(select(Category).where(Category.slug == slug)).scalar_one_or_none()
    if category:
        return category
    category = Category(slug=slug, name=name or slug)
    db.add(category)
    db.flush()
    return category


def _apply_upsert(db, source: Source, item: NormalizedPosting):
    """Returns (posting, event) where event is one of 'new', 'changed', None."""
    employer = _get_or_create_employer(db, item.employer_name)
    category = _get_or_create_category(db, item.category_slug, item.category_name)
    new_hash = content_hash(item.title, item.employer_name, item.location)

    existing = db.execute(
        select(Posting).where(Posting.source_id == source.id, Posting.external_id == item.external_id)
    ).scalar_one_or_none()

    if existing is None:
        # Cross-source dedup: check recent postings with a similar fingerprint
        duplicate_of_id = None
        candidates = db.execute(
            select(Posting).where(Posting.content_hash == new_hash, Posting.source_id != source.id)
        ).scalars().all()
        for candidate in candidates:
            if is_duplicate(
                item.title, item.employer_name, item.location,
                candidate.title, candidate.employer.name if candidate.employer else "", candidate.location,
            ):
                duplicate_of_id = candidate.duplicate_of_id or candidate.id
                break

        posting = Posting(
            source_id=source.id,
            employer_id=employer.id,
            category_id=category.id if category else None,
            external_id=item.external_id,
            title=item.title,
            description=item.description,
            location=item.location,
            seniority=item.seniority,
            employment_type=item.employment_type,
            salary_min=item.salary_min,
            salary_max=item.salary_max,
            salary_currency=item.salary_currency,
            url=item.url,
            posted_at=item.posted_at,
            closing_at=item.closing_at,
            is_active=True,
            content_hash=new_hash,
            duplicate_of_id=duplicate_of_id,
        )
        db.add(posting)
        db.flush()
        return posting, "new"

    changed_fields = []
    field_map = {
        "title": item.title,
        "location": item.location,
        "salary_min": item.salary_min,
        "salary_max": item.salary_max,
        "closing_at": item.closing_at,
        "is_active": True,
    }
    for field, new_value in field_map.items():
        old_value = getattr(existing, field)
        if old_value != new_value:
            db.add(PostingHistory(
                posting_id=existing.id,
                field_changed=field,
                old_value=str(old_value) if old_value is not None else None,
                new_value=str(new_value) if new_value is not None else None,
            ))
            setattr(existing, field, new_value)
            changed_fields.append(field)

    existing.content_hash = new_hash
    if changed_fields:
        db.flush()
        return existing, "changed"
    return existing, None


def _close_missing_postings(db, source: Source, seen_external_ids: set[str]) -> list[Posting]:
    stale = db.execute(
        select(Posting).where(
            Posting.source_id == source.id,
            Posting.is_active.is_(True),
            Posting.external_id.notin_(seen_external_ids) if seen_external_ids else True,
        )
    ).scalars().all()

    closed = []
    for posting in stale:
        db.add(PostingHistory(
            posting_id=posting.id, field_changed="is_active", old_value="True", new_value="False"
        ))
        posting.is_active = False
        closed.append(posting)
    if closed:
        db.flush()
    return closed


@shared_task(name="tasks.scrape_source", bind=True, max_retries=3, default_retry_delay=60)
def scrape_source(self, source_slug: str):
    logger.info("scrape_started", source=source_slug)
    scraper = get_scraper(source_slug)

    try:
        items = asyncio.run(scraper.run())
    except Exception as exc:  # noqa: BLE001
        logger.error("scrape_fetch_failed", source=source_slug, error=str(exc))
        raise self.retry(exc=exc)

    new_postings, changed_postings = [], []

    with SyncSessionLocal() as db:
        source = db.execute(select(Source).where(Source.slug == source_slug)).scalar_one_or_none()
        if source is None:
            source = Source(slug=scraper.slug, name=scraper.name, base_url=scraper.base_url, is_active=True)
            db.add(source)
            db.flush()

        seen_ids = set()
        for item in items:
            seen_ids.add(item.external_id)
            posting, event = _apply_upsert(db, source, item)
            if event == "new":
                new_postings.append(_posting_webhook_payload(posting))
            elif event == "changed":
                changed_postings.append(_posting_webhook_payload(posting))

        closed = _close_missing_postings(db, source, seen_ids)
        closed_payloads = [_posting_webhook_payload(p) for p in closed]

        db.commit()

    logger.info(
        "scrape_finished", source=source_slug, new=len(new_postings),
        changed=len(changed_postings), closed=len(closed_payloads),
    )

    from app.tasks.notifications import notify_closed_postings, notify_new_postings, notify_posting_changed

    if new_postings:
        notify_new_postings.delay(new_postings)
    if changed_postings:
        notify_posting_changed.delay(changed_postings)
    if closed_payloads:
        notify_closed_postings.delay(closed_payloads)


def _posting_webhook_payload(posting: Posting) -> dict:
    return {
        "id": posting.id,
        "title": posting.title,
        "url": posting.url,
        "employerId": posting.employer_id,
        "isActive": posting.is_active,
    }
