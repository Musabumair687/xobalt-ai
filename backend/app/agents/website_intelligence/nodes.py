"""LangGraph nodes for the Website Intelligence workflow."""

import logging
from app.agents.website_intelligence.state import WebsiteIntelligenceState
from app.services.page_discovery_service import PageDiscoveryService
from app.services.content_extraction_service import ContentExtractionService
from app.services.intelligence_service import IntelligenceService

logger = logging.getLogger(__name__)


async def discover_pages(
    state: WebsiteIntelligenceState,
    discovery_service: PageDiscoveryService
) -> dict:
    url = state.get("website_url")
    if not url:
        return {"errors": state.get("errors", []) + ["No website_url provided"]}
        
    logger.info(f"Discovering pages for {url}")
    pages = await discovery_service.discover(url, max_pages=5)
    
    if not pages:
         return {"errors": state.get("errors", []) + [f"No pages found for {url}"]}
         
    return {"discovered_pages": pages}


async def fetch_content(
    state: WebsiteIntelligenceState,
    extraction_service: ContentExtractionService
) -> dict:
    pages = state.get("discovered_pages", [])
    if not pages:
        return {}
        
    logger.info(f"Fetching and cleaning {len(pages)} pages")
    fetched = await extraction_service.process_pages(pages)
    
    if not fetched:
         return {"errors": state.get("errors", []) + ["Failed to fetch any pages successfully"]}
         
    return {"fetched_pages": fetched}


async def extract_intelligence(
    state: WebsiteIntelligenceState,
    intelligence_service: IntelligenceService
) -> dict:
    fetched = state.get("fetched_pages", [])
    if not fetched:
        return {}
        
    try:
        intel = await intelligence_service.extract(fetched)
        return {"extracted_intelligence": intel}
    except Exception as e:
        return {"errors": state.get("errors", []) + [f"LLM extraction failed: {str(e)}"]}
