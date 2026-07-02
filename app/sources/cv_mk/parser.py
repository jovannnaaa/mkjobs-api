"""JSON parsing/normalization for the 'cv_mk' source.

Assumes the portal exposes a paginated JSON listings endpoint. Field names
below are illustrative placeholders — adjust to the real payload shape.
"""
from datetime import datetime, timezone

from app.sources.base import NormalizedPosting


def parse_listing(payload: dict) -> list[NormalizedPosting]:
    postings: list[NormalizedPosting] = []

    for item in payload.get("results", []):
        try:
            posted_at = (
                datetime.fromisoformat(item["postedAt"])
                if item.get("postedAt")
                else datetime.now(timezone.utc)
            )
            closing_at = datetime.fromisoformat(item["closingAt"]) if item.get("closingAt") else None
        except (KeyError, ValueError):
            posted_at = datetime.now(timezone.utc)
            closing_at = None

        postings.append(
            NormalizedPosting(
                external_id=str(item.get("id")),
                title=item.get("title", "").strip(),
                employer_name=item.get("company", "").strip(),
                description=item.get("description"),
                location=item.get("location"),
                seniority=item.get("level"),
                employment_type=item.get("type"),
                salary_min=item.get("salaryMin"),
                salary_max=item.get("salaryMax"),
                salary_currency=item.get("currency", "MKD"),
                url=item.get("url", ""),
                posted_at=posted_at,
                closing_at=closing_at,
                category_slug=item.get("categorySlug"),
                category_name=item.get("categoryName"),
            )
        )

    return postings
