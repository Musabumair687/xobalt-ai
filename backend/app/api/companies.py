"""Companies API — Discovered Companies Directory & Website Intelligence."""

from __future__ import annotations

import logging
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.dependencies import get_db
from app.models.company import Company
from app.models.company_intelligence import CompanyIntelligence
from app.models.website import Website
from app.models.lead import Lead

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/companies", tags=["Companies"])


@router.get("", summary="List all discovered companies with website intelligence")
async def list_companies(
    industry: Optional[str] = Query(None, description="Filter by industry"),
    query: Optional[str] = Query(None, description="Search company name or domain"),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve all discovered companies enriched with live website intelligence."""
    stmt = (
        select(Company)
        .options(
            selectinload(Company.intelligence),
            selectinload(Company.leads),
        )
        .order_by(desc(Company.created_at))
    )

    if industry:
        stmt = stmt.where(Company.industry.ilike(f"%{industry}%"))

    if query:
        stmt = stmt.where(
            (Company.name.ilike(f"%{query}%")) | (Company.domain.ilike(f"%{query}%"))
        )

    res = await db.execute(stmt)
    companies = res.scalars().all()

    output = []
    for c in companies:
        intel = c.intelligence
        leads_count = len(c.leads or [])

        intel_data = None
        if intel:
            intel_data = {
                "services": intel.services or [],
                "unique_selling_points": intel.unique_selling_points or [],
                "target_market": intel.target_market or [],
                "technology": intel.technology or [],
                "locations": intel.locations or [],
                "confidence_score": intel.confidence_score,
                "pages_analyzed": intel.pages_analyzed or 1,
            }

        output.append({
            "id": str(c.id),
            "name": c.name,
            "domain": c.domain,
            "industry": c.industry,
            "employee_count": c.employee_count,
            "website_url": c.website_url or (f"https://{c.domain}" if c.domain else None),
            "city": c.city,
            "state": c.state,
            "country": c.country,
            "leads_count": leads_count,
            "intelligence": intel_data,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        })

    return output


@router.get("/{company_id}", summary="Get detailed intelligence for a specific company")
async def get_company_details(company_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Fetch complete details, intelligence, and associated contacts for a company."""
    stmt = (
        select(Company)
        .options(
            selectinload(Company.intelligence),
            selectinload(Company.leads).selectinload(Lead.person),
        )
        .where(Company.id == company_id)
    )
    res = await db.execute(stmt)
    c = res.scalars().first()

    if not c:
        return {"error": "Company not found"}

    intel = c.intelligence
    return {
        "id": str(c.id),
        "name": c.name,
        "domain": c.domain,
        "industry": c.industry,
        "employee_count": c.employee_count,
        "website_url": c.website_url,
        "city": c.city,
        "state": c.state,
        "country": c.country,
        "intelligence": {
            "services": intel.services if intel else [],
            "unique_selling_points": intel.unique_selling_points if intel else [],
            "target_market": intel.target_market if intel else [],
            "technology": intel.technology if intel else [],
            "locations": intel.locations if intel else [],
            "evidence": intel.evidence if intel else {},
            "confidence_score": intel.confidence_score if intel else None,
        } if intel else None,
        "leads": [
            {
                "id": str(l.id),
                "score": l.score,
                "status": l.status,
                "person": {
                    "name": f"{l.person.first_name} {l.person.last_name}" if l.person else "Unknown",
                    "title": l.person.title if l.person else None,
                } if l.person else None
            }
            for l in (c.leads or [])
        ]
    }
