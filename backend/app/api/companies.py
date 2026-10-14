"""Companies API — Discovered Companies Directory & Website Intelligence."""

from __future__ import annotations

import logging
import uuid
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, desc, func
from sqlalchemy.orm import selectinload, with_loader_criteria
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.dependencies import get_db
from app.models.company import Company
from app.models.company_intelligence import CompanyIntelligence
from app.models.website import Website
from app.models.lead import Lead
from app.models.person import Person
from app.models.user import User
from app.auth import get_current_user
from app.schemas.common import PaginatedResponse
from app.schemas.contracts import CompanyListItem

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/companies", tags=["Companies"])


@router.get(
    "",
    response_model=PaginatedResponse[CompanyListItem],
    summary="List discovered companies with website intelligence",
)
async def list_companies(
    current_user: User = Depends(get_current_user),
    industry: Annotated[Optional[str], Query(description="Filter by industry")] = None,
    query: Annotated[Optional[str], Query(description="Search company name or domain")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    db: AsyncSession = Depends(get_db)
):
    """Retrieve a page of discovered companies enriched with website intelligence."""
    stmt = (
        select(Company)
        .where(Company.organization_id == current_user.organization_id)
        .options(
            selectinload(Company.intelligence),
            selectinload(Company.leads),
            with_loader_criteria(
                Lead,
                Lead.organization_id == current_user.organization_id,
                include_aliases=True,
            ),
        )
        .order_by(desc(Company.created_at))
    )

    if industry:
        stmt = stmt.where(Company.industry.ilike(f"%{industry}%"))

    if query:
        stmt = stmt.where(
            (Company.name.ilike(f"%{query}%")) | (Company.domain.ilike(f"%{query}%"))
        )

    total = await db.scalar(
        select(func.count()).select_from(stmt.order_by(None).subquery())
    ) or 0
    res = await db.execute(stmt.offset((page - 1) * page_size).limit(page_size))
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

    return {
        "items": output,
        "page": page,
        "page_size": page_size,
        "total": total,
        "pages": (total + page_size - 1) // page_size,
    }


@router.get("/{company_id}", summary="Get detailed intelligence for a specific company")
async def get_company_details(
    company_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Fetch complete details, intelligence, and associated contacts for a company."""
    stmt = (
        select(Company)
        .options(
            selectinload(Company.intelligence),
            selectinload(Company.leads).selectinload(Lead.person),
            with_loader_criteria(
                Lead,
                Lead.organization_id == current_user.organization_id,
                include_aliases=True,
            ),
            with_loader_criteria(
                Person,
                Person.organization_id == current_user.organization_id,
                include_aliases=True,
            ),
        )
        .where(
            Company.id == company_id,
            Company.organization_id == current_user.organization_id,
        )
    )
    res = await db.execute(stmt)
    c = res.scalars().first()

    if not c:
        raise HTTPException(status_code=404, detail="Company not found")

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
