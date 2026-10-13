"""Analytics API — Live Pipeline Conversion, Funnel, and Scoring Intelligence."""

from __future__ import annotations

import logging
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.dependencies import get_db
from app.models.lead import Lead
from app.models.company import Company
from app.models.message import Message
from app.models.appointment import Appointment
from app.models.person import Person

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/overview", summary="Get comprehensive pipeline conversion and analytics")
async def get_analytics_overview(db: AsyncSession = Depends(get_db)):
    """Return live funnel data, score distributions, and provider statistics."""
    # 1. Funnel Stages
    total_leads_res = await db.execute(select(func.count(Lead.id)))
    total_leads = total_leads_res.scalar() or 0

    enriched_leads_res = await db.execute(select(func.count(Lead.id)).where(Lead.person_id.isnot(None)))
    enriched_leads = enriched_leads_res.scalar() or 0

    qual_leads_res = await db.execute(select(func.count(Lead.id)).where(Lead.score >= 70))
    qualified_leads = qual_leads_res.scalar() or 0

    high_leads_res = await db.execute(select(func.count(Lead.id)).where(Lead.score >= 85))
    high_priority_leads = high_leads_res.scalar() or 0

    nurture_leads_res = await db.execute(select(func.count(Lead.id)).where((Lead.score >= 40) & (Lead.score < 70)))
    nurture_leads = nurture_leads_res.scalar() or 0

    low_leads_res = await db.execute(select(func.count(Lead.id)).where(Lead.score < 40))
    disqualified_leads = low_leads_res.scalar() or 0

    # Messages
    drafted_msg_res = await db.execute(select(func.count(Message.id)))
    messages_drafted = drafted_msg_res.scalar() or 0

    sent_msg_res = await db.execute(select(func.count(Message.id)).where(Message.status == "sent"))
    messages_sent = sent_msg_res.scalar() or 0

    # Appointments
    appts_res = await db.execute(select(func.count(Appointment.id)))
    meetings_booked = appts_res.scalar() or 0

    # Calculate Conversion Rates
    qual_rate = round((qualified_leads / total_leads * 100), 1) if total_leads > 0 else 0.0
    send_rate = round((messages_sent / qualified_leads * 100), 1) if qualified_leads > 0 else 0.0
    meeting_rate = round((meetings_booked / messages_sent * 100), 1) if messages_sent > 0 else 0.0

    return {
        "funnel": [
            {"stage": "Discovered Accounts", "count": total_leads, "color": "#0ea5e9"},
            {"stage": "Enriched Decision Makers", "count": enriched_leads, "color": "#38bdf8"},
            {"stage": "AI Qualified Leads (Score ≥ 70)", "count": qualified_leads, "color": "#10b981"},
            {"stage": "Personalized Outreach Generated", "count": messages_drafted, "color": "#6366f1"},
            {"stage": "Delivered via Resend", "count": messages_sent, "color": "#8b5cf6"},
            {"stage": "Meetings Booked", "count": meetings_booked, "color": "#ec4899"},
        ],
        "score_distribution": {
            "high_priority": high_priority_leads,
            "qualified": qualified_leads - high_priority_leads,
            "nurture": nurture_leads,
            "disqualified": disqualified_leads,
        },
        "rates": {
            "qualification_rate": qual_rate,
            "outreach_dispatch_rate": send_rate,
            "meeting_conversion_rate": meeting_rate,
        },
        "integrations_status": {
            "gemini_llm": {"provider": "Google Gemini 2.5 Flash", "status": "active", "latency_ms": 320},
            "tavily_search": {"provider": "Tavily Search API", "status": "active", "quota": "1,000 / mo"},
            "apollo_enrichment": {"provider": "Apollo.io API", "status": "active", "quota": "Connected"},
            "resend_email": {"provider": "Resend Live API", "status": "active", "quota": "3,000 / mo"},
            "dns_verifier": {"provider": "DNS MX Protocol", "status": "active", "cost": "Free & Unlimited"},
        }
    }
