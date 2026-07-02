"""Registry mapping source slugs to their Scraper implementations and
Celery Beat schedules. New portals are added here.
"""
from app.sources.base import Scraper
from app.sources.cv_mk.scraper import CvMkScraper
from app.sources.cv_mk.schedule import SCHEDULE as CV_MK_SCHEDULE
from app.sources.vrabotuvanje.scraper import VrabotuvanjeScraper
from app.sources.vrabotuvanje.schedule import SCHEDULE as VRABOTUVANJE_SCHEDULE

SCRAPERS: dict[str, type[Scraper]] = {
    VrabotuvanjeScraper.slug: VrabotuvanjeScraper,
    CvMkScraper.slug: CvMkScraper,
}

SCHEDULES: dict[str, dict] = {
    VrabotuvanjeScraper.slug: VRABOTUVANJE_SCHEDULE,
    CvMkScraper.slug: CV_MK_SCHEDULE,
}


def get_scraper(slug: str) -> Scraper:
    if slug not in SCRAPERS:
        raise KeyError(f"Unknown source slug: {slug}")
    return SCRAPERS[slug]()
