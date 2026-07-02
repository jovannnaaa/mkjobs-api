"""Base contract for per-portal scraper strategies.

Each source under app/sources/<portal>/ implements a Scraper subclass with
fetch() and parse(), and a NormalizedPosting output consumed by the
deduplication + upsert pipeline in app/tasks/scraping.py.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass
class NormalizedPosting:
    external_id: str
    title: str
    employer_name: str
    description: str | None
    location: str | None
    seniority: str | None
    employment_type: str | None
    salary_min: float | None
    salary_max: float | None
    salary_currency: str | None
    url: str
    posted_at: datetime
    closing_at: datetime | None
    category_slug: str | None
    category_name: str | None


class Scraper(ABC):
    """One implementation per job portal / source."""

    slug: str
    name: str
    base_url: str

    @abstractmethod
    async def fetch(self) -> str:
        """Retrieve raw listing content (HTML/JSON) from the source."""
        raise NotImplementedError

    @abstractmethod
    def parse(self, raw: str) -> list[NormalizedPosting]:
        """Parse raw content into normalized posting records."""
        raise NotImplementedError

    async def run(self) -> list[NormalizedPosting]:
        raw = await self.fetch()
        return self.parse(raw)
