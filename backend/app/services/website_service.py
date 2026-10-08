"""Application service for Website Intelligence persistence.

Handles retrieving companies, saving discovered pages, and saving
the final structured intelligence back to PostgreSQL.
"""

import uuid
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.company import Company
from app.models.website import Website
from app.models.website_page import WebsitePage
from app.models.company_intelligence import CompanyIntelligence
from app.schemas.website_intelligence import FetchedPage, IntelligenceWithEvidence

class WebsiteService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_company_url(self, company_id: uuid.UUID) -> Optional[str]:
        """Get the website URL for a company."""
        result = await self.db.execute(select(Company).where(Company.id == company_id))
        company = result.scalars().first()
        if not company or not company.domain:
            # We construct a URL from domain if website_url is null
            if company and company.website_url:
                return company.website_url
            return None
            
        url = company.domain
        if not url.startswith("http"):
            url = f"https://{url}"
        return url

    async def get_or_create_website(self, company_id: uuid.UUID, url: str) -> Website:
        """Find or create the Website tracking record."""
        result = await self.db.execute(select(Website).where(Website.company_id == company_id))
        website = result.scalars().first()
        
        if not website:
            website = Website(company_id=company_id, url=url, status="pending")
            self.db.add(website)
            await self.db.flush()
            
        return website

    async def save_pages(self, website_id: uuid.UUID, pages: list[FetchedPage]):
        """Save fetched pages to the database."""
        # Clear old pages for this website to avoid duplicate tracking in Phase 4
        await self.db.execute(
            WebsitePage.__table__.delete().where(WebsitePage.website_id == website_id)
        )
        
        for p in pages:
            wp = WebsitePage(
                website_id=website_id,
                url=p.url,
                page_type=p.page_type.value,
                title=p.title,
                content_length=p.content_length,
                status_code=p.status_code,
                status="completed" if p.status_code == 200 else "failed"
            )
            self.db.add(wp)
        await self.db.flush()

    async def save_intelligence(self, company_id: uuid.UUID, website_id: uuid.UUID, data: IntelligenceWithEvidence):
        """Save extracted intelligence to the database."""
        result = await self.db.execute(
            select(CompanyIntelligence).where(CompanyIntelligence.company_id == company_id)
        )
        intel = result.scalars().first()
        
        if not intel:
            intel = CompanyIntelligence(company_id=company_id, website_id=website_id)
            self.db.add(intel)
            
        # Update fields
        extracted = data.intelligence
        intel.services = extracted.services
        intel.target_market = extracted.target_market
        intel.locations = extracted.locations
        intel.unique_selling_points = extracted.unique_selling_points
        intel.projects = extracted.projects
        intel.contact_info = extracted.contact_info
        intel.technology = extracted.technology
        
        intel.evidence = data.evidence
        intel.confidence_score = data.confidence
        intel.pages_analyzed = data.pages_analyzed
        intel.llm_model_used = data.model_used
        
        await self.db.flush()
        
        # Update website status
        website_result = await self.db.execute(select(Website).where(Website.id == website_id))
        website = website_result.scalars().first()
        if website:
            website.status = "completed"
            website.crawl_count += 1
            
        await self.db.commit()
