"""Seed the database with a handful of sample postings for local development
and academic demo purposes (no live scraping required).

Usage:
    python -m scripts.seed
"""
import asyncio
from datetime import datetime, timedelta, timezone

from app.core.db import AsyncSessionLocal
from app.models import Category, Employer, Posting, Source
from app.tasks.dedup import content_hash

SAMPLE_SOURCES = [
    {"slug": "vrabotuvanje", "name": "Vrabotuvanje.com.mk", "base_url": "https://www.vrabotuvanje.com.mk"},
    {"slug": "cv_mk", "name": "CV.mk", "base_url": "https://www.cv.mk"},
]

SAMPLE_CATEGORIES = [
    {"slug": "software-engineering", "name": "Software Engineering"},
    {"slug": "marketing", "name": "Marketing"},
    {"slug": "customer-support", "name": "Customer Support"},
]

SAMPLE_EMPLOYERS = [
    {"name": "Skopje Tech Solutions", "normalized_name": "skopje tech solutions", "location": "Skopje"},
    {"name": "Ohrid Digital Agency", "normalized_name": "ohrid digital agency", "location": "Ohrid"},
]


async def seed():
    async with AsyncSessionLocal() as db:
        sources = {}
        for s in SAMPLE_SOURCES:
            src = Source(**s)
            db.add(src)
            sources[s["slug"]] = src

        categories = {}
        for c in SAMPLE_CATEGORIES:
            cat = Category(**c)
            db.add(cat)
            categories[c["slug"]] = cat

        employers = []
        for e in SAMPLE_EMPLOYERS:
            emp = Employer(**e)
            db.add(emp)
            employers.append(emp)

        await db.flush()

        now = datetime.now(timezone.utc)
        postings = [
            Posting(
                source_id=sources["vrabotuvanje"].id,
                employer_id=employers[0].id,
                category_id=categories["software-engineering"].id,
                external_id="vr-1001",
                title="Backend Developer (Python)",
                description="Join our backend team building scalable APIs.",
                location="Skopje",
                seniority="mid",
                employment_type="full_time",
                salary_min=45000,
                salary_max=65000,
                salary_currency="MKD",
                url="https://www.vrabotuvanje.com.mk/oglasi/1001",
                posted_at=now - timedelta(days=1),
                closing_at=now + timedelta(days=20),
                is_active=True,
                content_hash=content_hash("Backend Developer (Python)", "Skopje Tech Solutions", "Skopje"),
            ),
            Posting(
                source_id=sources["cv_mk"].id,
                employer_id=employers[1].id,
                category_id=categories["marketing"].id,
                external_id="cv-2002",
                title="Digital Marketing Specialist",
                description="Plan and run campaigns across social platforms.",
                location="Ohrid",
                seniority="junior",
                employment_type="full_time",
                salary_min=30000,
                salary_max=40000,
                salary_currency="MKD",
                url="https://www.cv.mk/listings/2002",
                posted_at=now - timedelta(days=3),
                closing_at=now + timedelta(days=10),
                is_active=True,
                content_hash=content_hash("Digital Marketing Specialist", "Ohrid Digital Agency", "Ohrid"),
            ),
        ]
        db.add_all(postings)
        await db.commit()
        print(f"Seeded {len(postings)} postings.")


if __name__ == "__main__":
    asyncio.run(seed())
