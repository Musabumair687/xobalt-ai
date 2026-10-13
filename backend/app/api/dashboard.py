"""Dashboard API — Live statistics and pipeline metrics for Next.js frontend."""

from __future__ import annotations

import logging
from fastapi import APIRouter, Depends
from sqlalchemy import select, func, desc
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.dependencies import get_db
from app.config import get_settings
from app.models.lead import Lead
from app.models.company import Company
from app.models.person import Person
from app.models.contact import Contact
from app.models.message import Message
from app.models.appointment import Appointment

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary", summary="Get live pipeline summary metrics")
async def get_dashboard_summary(db: AsyncSession = Depends(get_db)):
    """Return live metrics from the database."""
    settings = get_settings()

    # Count total leads
    leads_count_res = await db.execute(select(func.count(Lead.id)))
    total_leads = leads_count_res.scalar() or 0

    # Count qualified leads (score >= 70)
    qual_count_res = await db.execute(select(func.count(Lead.id)).where(Lead.score >= 70))
    qualified_leads = qual_count_res.scalar() or 0

    # Count companies
    comp_count_res = await db.execute(select(func.count(Company.id)))
    total_companies = comp_count_res.scalar() or 0

    # Count messages
    sent_count_res = await db.execute(select(func.count(Message.id)).where(Message.status == "sent"))
    messages_sent = sent_count_res.scalar() or 0

    draft_count_res = await db.execute(select(func.count(Message.id)).where(Message.status != "sent"))
    messages_drafted = draft_count_res.scalar() or 0

    # Count meetings
    meet_count_res = await db.execute(select(func.count(Appointment.id)))
    meetings_booked = meet_count_res.scalar() or 0

    # Recent Discovered Leads (latest 8)
    recent_leads_res = await db.execute(
        select(Lead)
        .options(
            selectinload(Lead.company),
            selectinload(Lead.person).selectinload(Person.contacts),
            selectinload(Lead.messages),
        )
        .order_by(desc(Lead.created_at))
        .limit(8)
    )
    recent_leads = recent_leads_res.scalars().all()

    recent_discoveries = []
    recent_activity = []
    for l in recent_leads:
        comp_name = l.company.name if l.company else "Unknown Company"
        comp_domain = (l.company.domain if l.company else "") or ""
        website_url = (l.company.website_url if l.company else "") or (f"https://{comp_domain}" if comp_domain else "")
        industry = (l.company.industry if l.company else "") or "Commercial"

        p_name = f"{l.person.first_name} {l.person.last_name}".strip() if l.person else "Unassigned Contact"
        p_title = (l.person.title if l.person and l.person.title else "Decision Maker") if l.person else "General Inbox"

        # Email & verification status
        p_contacts = l.person.contacts if l.person else []
        email = next((c.value for c in p_contacts if c.type == "email"), None)
        is_verified = any(c.is_verified for c in p_contacts if c.type == "email")
        email_status = "verified" if is_verified else ("deliverable" if email else "domain_contact")

        score_val = int(l.score) if l.score is not None else None
        qual_status = "Qualified" if (l.score and l.score >= 70) else ("Review" if (l.score and l.score >= 50) else "New")

        # Has outreach message drafted or sent?
        msg_status = "not_started"
        if l.messages:
            msg = l.messages[0]
            msg_status = msg.status  # "draft" or "sent"

        recent_discoveries.append({
            "id": str(l.id),
            "company_name": comp_name,
            "company_domain": comp_domain,
            "website_url": website_url,
            "industry": industry,
            "decision_maker_name": p_name,
            "decision_maker_title": p_title,
            "email": email,
            "email_status": email_status,
            "score": score_val,
            "qualification_status": qual_status,
            "message_status": msg_status,
            "created_at": l.created_at.isoformat() if l.created_at else None,
        })

        score_str = f"Score: {score_val}" if score_val is not None else "Discovered"
        recent_activity.append({
            "title": comp_name,
            "sub": f"Lead {score_str} • {p_title}",
            "time": l.created_at.strftime("%I:%M %p") if l.created_at else "Just now",
            "status": qual_status
        })

    # Active LLM configuration
    active_model = settings.GEMINI_MODEL if settings.LLM_PROVIDER == "gemini" else settings.GROQ_MODEL
    active_provider = settings.LLM_PROVIDER.capitalize()

    # Dynamic integrations status based on configuration
    integrations = {
        "llm": {
            "name": f"{active_provider} ({active_model})",
            "status": "connected" if (settings.GEMINI_API_KEY or settings.GROQ_API_KEY) else "unconfigured",
            "provider": settings.LLM_PROVIDER,
        },
        "search": {
            "name": "Tavily Search" if settings.TAVILY_API_KEY else "DuckDuckGo Free",
            "status": "connected" if settings.TAVILY_API_KEY else "free_tier",
            "provider": "tavily" if settings.TAVILY_API_KEY else "ddg",
        },
        "enrichment": {
            "name": "Apollo.io Live",
            "status": "connected" if settings.APOLLO_API_KEY else "unconfigured",
            "provider": "apollo",
        },
        "verification": {
            "name": "DNS MX Deliverability",
            "status": "connected",
            "provider": "dns",
        },
        "email": {
            "name": "Resend API",
            "status": "connected" if settings.RESEND_API_KEY else "smtp",
            "provider": "resend" if settings.RESEND_API_KEY else "smtp",
        }
    }

    return {
        "total_leads": total_leads,
        "qualified_leads": qualified_leads,
        "total_companies": total_companies,
        "messages_sent": messages_sent,
        "messages_drafted": messages_drafted,
        "meetings_booked": meetings_booked,
        "active_model": active_model,
        "llm_provider": active_provider,
        "recent_discoveries": recent_discoveries,
        "recent_activity": recent_activity,
        "integrations": integrations
    }
