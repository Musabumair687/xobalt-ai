"""API router for Website Intelligence."""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.dependencies import get_db
from app.config import get_settings
from app.schemas.website_intelligence import (
    WebsiteIntelligenceRequest, 
    WebsiteIntelligenceResponse, 
    CrawlStatus
)
from app.services.website_service import WebsiteService
from app.services.page_discovery_service import PageDiscoveryService
from app.services.content_extraction_service import ContentExtractionService
from app.services.intelligence_service import IntelligenceService
from app.integrations.website.http_client import HttpFetcher
from app.workflows.website_intelligence_workflow import build_website_intelligence_graph

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/website-intelligence", tags=["Website Intelligence"])


def get_llm():
    """Factory to return configured LLM."""
    settings = get_settings()
    if settings.LLM_PROVIDER == "groq":
        try:
            from langchain_groq import ChatGroq
            return ChatGroq(api_key=settings.GROQ_API_KEY, model_name=settings.GROQ_MODEL)
        except ImportError:
            raise RuntimeError("langchain-groq not installed or API key missing.")
    elif settings.LLM_PROVIDER == "gemini":
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(google_api_key=settings.GEMINI_API_KEY, model=settings.GEMINI_MODEL)
        except ImportError:
            raise RuntimeError("langchain-google-genai not installed or API key missing.")
    else:
         raise ValueError(f"Unknown LLM provider: {settings.LLM_PROVIDER}")


@router.post(
    "/analyze",
    response_model=WebsiteIntelligenceResponse,
    status_code=status.HTTP_202_ACCEPTED
)
async def analyze_website(
    request: WebsiteIntelligenceRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Trigger website intelligence analysis for a company."""
    
    website_service = WebsiteService(db)
    
    # 1. Resolve URL
    url = await website_service.get_company_url(request.company_id)
    if not url:
        raise HTTPException(
            status_code=400, 
            detail=f"Company {request.company_id} has no domain or website URL."
        )
        
    # 2. Get or create website record
    website = await website_service.get_or_create_website(request.company_id, url)
    
    # Check if we should skip
    if website.status == "completed" and not request.force_recrawl:
        return WebsiteIntelligenceResponse(
            company_id=request.company_id,
            website_url=url,
            status=CrawlStatus.completed,
            errors=["Analysis already completed. Use force_recrawl=True to run again."]
        )
        
    # Set to crawling
    website.status = "crawling"
    await db.commit()

    # 3. Setup services for the workflow
    settings = get_settings()
    fetcher = HttpFetcher(timeout=settings.CRAWL_TIMEOUT)
    
    discovery = PageDiscoveryService(fetcher)
    extraction = ContentExtractionService(fetcher)
    intelligence = IntelligenceService(get_llm())
    
    graph = build_website_intelligence_graph(discovery, extraction, intelligence)
    
    initial_state = {
        "company_id": request.company_id,
        "website_url": url,
        "errors": []
    }

    # 4. Background task runner
    async def _run_workflow():
        # Create a new isolated session for the background task
        from app.database.session import AsyncSessionLocal
        async with AsyncSessionLocal() as bg_db:
            bg_website_service = WebsiteService(bg_db)
            
            try:
                final_state = await graph.ainvoke(initial_state)
                errors = final_state.get("errors", [])
                
                # Save pages
                fetched_pages = final_state.get("fetched_pages", [])
                if fetched_pages:
                    await bg_website_service.save_pages(website.id, fetched_pages)
                
                # Save intelligence
                intel = final_state.get("extracted_intelligence")
                if intel and not errors:
                    await bg_website_service.save_intelligence(request.company_id, website.id, intel)
                else:
                    # Mark failed
                    bg_website = await bg_website_service.get_or_create_website(request.company_id, url)
                    bg_website.status = "failed"
                    await bg_db.commit()
                    logger.error(f"Website Intelligence failed for {url}: {errors}")
                    
            except Exception as e:
                logger.error(f"Website Intelligence workflow crashed for {url}: {e}")
                bg_website = await bg_website_service.get_or_create_website(request.company_id, url)
                bg_website.status = "failed"
                await bg_db.commit()

    background_tasks.add_task(_run_workflow)

    return WebsiteIntelligenceResponse(
        company_id=request.company_id,
        website_url=url,
        status=CrawlStatus.crawling
    )
