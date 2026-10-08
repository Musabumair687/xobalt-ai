"""Service for finding relevant pages on a company website.

Uses heuristics and common paths to discover /about, /services, etc.
"""

from app.integrations.website.base import WebsiteFetcher
from app.integrations.website.parser import extract_links
from app.schemas.website_intelligence import DiscoveredPage, PageType


class PageDiscoveryService:
    def __init__(self, fetcher: WebsiteFetcher):
        self.fetcher = fetcher

    def categorize_url(self, url: str) -> PageType:
        """Heuristically determine the page type from its URL."""
        lower_url = url.lower()
        if any(x in lower_url for x in ["about", "company", "our-story", "who-we-are"]):
            return PageType.about
        if any(x in lower_url for x in ["service", "solution", "what-we-do", "expertise"]):
            return PageType.services
        if any(x in lower_url for x in ["contact", "get-in-touch", "let-us-talk"]):
            return PageType.contact
        if any(x in lower_url for x in ["project", "portfolio", "case-stud", "work"]):
            return PageType.projects
        if any(x in lower_url for x in ["team", "leadership"]):
            return PageType.team
        
        # If it's just the root or trailing slash, it's home
        if lower_url.endswith("/") and lower_url.count("/") <= 3:
             return PageType.home
             
        return PageType.other

    async def discover(self, root_url: str, max_pages: int = 5) -> list[DiscoveredPage]:
        """Fetch the root URL and discover other relevant pages."""
        pages: list[DiscoveredPage] = []
        
        # Always include the home page
        pages.append(DiscoveredPage(url=root_url, page_type=PageType.home))
        
        try:
            status, html = await self.fetcher.fetch(root_url)
            if status != 200 or not html:
                return pages
                
            links = extract_links(html, root_url)
            
            # Prioritize standard pages
            priority_types = {PageType.about, PageType.services, PageType.contact, PageType.projects}
            
            for link in links:
                if link == root_url or link + "/" == root_url:
                    continue
                    
                ptype = self.categorize_url(link)
                if ptype in priority_types:
                    # Avoid duplicates of same type
                    if not any(p.page_type == ptype for p in pages):
                        pages.append(DiscoveredPage(url=link, page_type=ptype))
                
                if len(pages) >= max_pages:
                    break
                    
        except Exception:
            pass # Return whatever we got (at least home)
            
        return pages
