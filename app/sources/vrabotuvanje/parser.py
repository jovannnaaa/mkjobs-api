"""HTML parsing/normalization for the 'vrabotuvanje' source.

NOTE: CSS selectors below are illustrative placeholders. Adjust them to the
real markup of the target listing pages before enabling this source in
production; the scraping task will simply skip a source that raises during
parse() and log the error rather than failing the whole run.
"""
from datetime import datetime, timezone

from bs4 import BeautifulSoup

from app.sources.base import NormalizedPosting


def parse_listing(raw_html: str, base_url: str) -> list[NormalizedPosting]:
    soup = BeautifulSoup(raw_html, "lxml")
    postings: list[NormalizedPosting] = []

    for card in soup.select(".job-listing-card"):
        external_id = card.get("data-job-id")
        title_el = card.select_one(".job-title")
        employer_el = card.select_one(".job-employer")
        location_el = card.select_one(".job-location")
        link_el = card.select_one("a.job-link")

        if not (external_id and title_el and employer_el and link_el):
            continue

        url = link_el.get("href", "")
        if url.startswith("/"):
            url = base_url.rstrip("/") + url

        postings.append(
            NormalizedPosting(
                external_id=str(external_id),
                title=title_el.get_text(strip=True),
                employer_name=employer_el.get_text(strip=True),
                description=None,
                location=location_el.get_text(strip=True) if location_el else None,
                seniority=None,
                employment_type=None,
                salary_min=None,
                salary_max=None,
                salary_currency="MKD",
                url=url,
                posted_at=datetime.now(timezone.utc),
                closing_at=None,
                category_slug=None,
                category_name=None,
            )
        )

    return postings
