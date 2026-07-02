import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.sources.base import NormalizedPosting, Scraper
from app.sources.vrabotuvanje.parser import parse_listing


class VrabotuvanjeScraper(Scraper):
    slug = "vrabotuvanje"
    name = "Vrabotuvanje.com.mk"
    base_url = "https://www.vrabotuvanje.com.mk"

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    async def fetch(self) -> str:
        headers = {"User-Agent": "MkJobsBot/1.0 (+https://mkjobs.example.mk)"}
        async with httpx.AsyncClient(timeout=15.0, headers=headers) as client:
            response = await client.get(f"{self.base_url}/oglasi")
            response.raise_for_status()
            return response.text

    def parse(self, raw: str) -> list[NormalizedPosting]:
        return parse_listing(raw, self.base_url)
