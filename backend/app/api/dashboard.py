"""Dashboard API — Live statistics and pipeline metrics for Next.js frontend."""

from __future__ import annotations

import logging
from fastapi import APIRouter, Depends
from sqlalchemy import select, func, desc
from sqlalchemy.orm import selectinload, with_loader_criteria
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.dependencies import get_db
from app.models.lead import Lead
from app.models.company import Company
from app.models.person import Person
from app.models.message import Message
from app.models.appointment import Appointment
from app.models.user import User
from app.auth import get_current_user
from app.schemas.contracts import DashboardSummaryResponse
from app.api.settings import get_settings_status
from app.services.integration_settings_service import get_organization_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get(
    "/summary",
    response_model=DashboardSummaryResponse,
    summary="Get live organization pipeline summary metrics",
)
async def get_dashboard_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return live metrics from the database."""
    settings = await get_organization_settings(db, current_user.organization_id)

    # Count total leads
    leads_count_res = await db.execute(
        select(func.count(Lead.id)).where(
            Lead.organization_id == current_user.organization_id
        )
    )
    total_leads = leads_count_res.scalar() or 0

    # Count qualified leads (score >= 70)
    qual_count_res = await db.execute(
        select(func.count(Lead.id)).where(
            Lead.organization_id == current_user.organization_id,
            Lead.score >= 70,
        )
    )
    qualified_leads = qual_count_res.scalar() or 0

    # Count companies
    comp_count_res = await db.execute(
        select(func.count(Company.id)).where(
            Company.organization_id == current_user.organization_id
        )
    )
    total_companies = comp_count_res.scalar() or 0

    # Count messages
    sent_count_res = await db.execute(
        select(func.count(Message.id)).where(
            Message.organization_id == current_user.organization_id,
            Message.status == "sent",
        )
    )
    messages_sent = sent_count_res.scalar() or 0

    draft_count_res = await db.execute(
        select(func.count(Message.id)).where(
            Message.organization_id == current_user.organization_id,
            Message.direction == "outbound",
            Message.status.in_(("draft", "pending_approval")),
        )
    )
    messages_drafted = draft_count_res.scalar() or 0

    # Count meetings
    meet_count_res = await db.execute(
        select(func.count(Appointment.id)).where(
            Appointment.organization_id == current_user.organization_id,
            Appointment.status.in_(("scheduled", "confirmed", "booked")),
        )
    )
    meetings_booked = meet_count_res.scalar() or 0

    # Recent Discovered Leads (latest 8)
    recent_leads_res = await db.execute(
        select(Lead)
        .where(Lead.organization_id == current_user.organization_id)
        .options(
            selectinload(Lead.company),
            selectinload(Lead.person).selectinload(Person.contacts),
            selectinload(Lead.messages),
            with_loader_criteria(
                Company,
                Company.organization_id == current_user.organization_id,
                include_aliases=True,
            ),
            with_loader_criteria(
                Person,
                Person.organization_id == current_user.organization_id,
                include_aliases=True,
            ),
            with_loader_criteria(
                Message,
                Message.organization_id == current_user.organization_id,
                include_aliases=True,
            ),
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
        email_status = "verified" if is_verified else ("unverified" if email else "no_email")

        score_val = int(l.score) if l.score is not None else None
        qual_status = "Qualified" if (score_val is not None and score_val >= 70) else ("Review" if (score_val is not None and score_val >= 50) else "New")

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

    configured = await get_settings_status(current_user, db)
    integrations_by_id = {item.id: item for item in configured.integrations}
    integrations = {
        "llm": integrations_by_id["llm"].model_dump(),
        "search": integrations_by_id["discovery"].model_dump(),
        "enrichment": integrations_by_id["enrichment"].model_dump(),
        "verification": integrations_by_id["verification"].model_dump(),
        "email": integrations_by_id["email"].model_dump(),
    }
    integrations["llm"]["name"] = f"{active_provider} ({active_model})"

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
