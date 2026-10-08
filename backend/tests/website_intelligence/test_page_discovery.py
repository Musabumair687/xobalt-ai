import pytest
from app.services.page_discovery_service import PageDiscoveryService
from app.integrations.website.base import WebsiteFetcher
from app.schemas.website_intelligence import PageType

class MockFetcher(WebsiteFetcher):
    def __init__(self, status=200, html=""):
        self.status = status
        self.html = html
        
    @property
    def name(self) -> str:
        return "mock"
        
    async def is_available(self) -> bool:
        return True
        
    async def fetch(self, url: str) -> tuple[int, str]:
        return self.status, self.html

def test_categorize_url():
    fetcher = MockFetcher()
    service = PageDiscoveryService(fetcher)
    
    assert service.categorize_url("https://test.com/about-us") == PageType.about
    assert service.categorize_url("https://test.com/our-services") == PageType.services
    assert service.categorize_url("https://test.com/contact") == PageType.contact
    assert service.categorize_url("https://test.com/portfolio") == PageType.projects
    assert service.categorize_url("https://test.com/team-members") == PageType.team
    assert service.categorize_url("https://test.com/") == PageType.home
    assert service.categorize_url("https://test.com/random-post-123") == PageType.other

@pytest.mark.asyncio
async def test_discover_pages_prioritizes_correctly():
    html = """
    <a href="/random-1">Random 1</a>
    <a href="/contact">Contact Us</a>
    <a href="/random-2">Random 2</a>
    <a href="/about">About</a>
    """
    fetcher = MockFetcher(html=html)
    service = PageDiscoveryService(fetcher)
    
    pages = await service.discover("https://test.com", max_pages=3)
    
    # Should get exactly 3 pages: home (always included), and the two priority ones we found
    assert len(pages) == 3
    
    types = [p.page_type for p in pages]
    assert PageType.home in types
    assert PageType.contact in types
    assert PageType.about in types
    assert PageType.other not in types # Should prioritize about/contact over random
