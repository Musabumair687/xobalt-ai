"""Service for fetching and cleaning website pages."""

import logging
from app.integrations.website.base import WebsiteFetcher
from app.integrations.website.parser import parse_html
from app.schemas.website_intelligence import DiscoveredPage, FetchedPage

logger = logging.getLogger(__name__)

class ContentExtractionService:
    def __init__(self, fetcher: WebsiteFetcher):
        self.fetcher = fetcher

    async def fetch_and_clean(self, page: DiscoveredPage) -> FetchedPage:
        """Fetch a single page and clean its HTML."""
        try:
            status, html = await self.fetcher.fetch(page.url)
            
            clean_text = ""
            if status == 200 and html:
                clean_text = parse_html(html)
                
            return FetchedPage(
                url=page.url,
                page_type=page.page_type,
                title=page.title,
                status_code=status,
                clean_text=clean_text,
                content_length=len(clean_text),
            )
        except Exception as e:
            logger.error(f"Failed to fetch {page.url}: {e}")
            return FetchedPage(
                url=page.url,
                page_type=page.page_type,
                status_code=500,
                clean_text="",
            )

    async def process_pages(self, pages: list[DiscoveredPage]) -> list[FetchedPage]:
        """Fetch and clean multiple pages sequentially (to avoid rate limits)."""
        results = []
        for p in pages:
            res = await self.fetch_and_clean(p)
            if res.status_code == 200 and res.clean_text:
                results.append(res)
        return results
