"""Organization-scoped, database-backed funnel analytics."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.settings import get_settings_status
from app.auth import get_current_user
from app.database.dependencies import get_db
from app.models.appointment import Appointment
from app.models.company import Company
from app.models.lead import Lead
from app.models.message import Message
from app.models.user import User
from app.schemas.contracts import AnalyticsOverviewResponse

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get(
    "/overview",
    response_model=AnalyticsOverviewResponse,
    summary="Get organization pipeline conversion analytics",
)
async def get_analytics_overview(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    org_id = current_user.organization_id

    async def count(model, *filters) -> int:
        result = await db.scalar(
            select(func.count()).select_from(model).where(*filters)
        )
        return int(result or 0)

    total_leads = await count(Lead, Lead.organization_id == org_id)
    enriched_leads = await count(
        Lead,
        Lead.organization_id == org_id,
        Lead.person_id.is_not(None),
    )
    qualified_leads = await count(
        Lead,
        Lead.organization_id == org_id,
        Lead.score >= 70,
    )
    high_priority_leads = await count(
        Lead,
        Lead.organization_id == org_id,
        Lead.score >= 85,
    )
    nurture_leads = await count(
        Lead,
        Lead.organization_id == org_id,
        Lead.score >= 40,
        Lead.score < 70,
    )
    disqualified_leads = await count(
        Lead,
        Lead.organization_id == org_id,
        Lead.score < 40,
    )
    unscored_leads = await count(
        Lead,
        Lead.organization_id == org_id,
        Lead.score.is_(None),
    )
    outbound_messages = await count(
        Message,
        Message.organization_id == org_id,
        Message.direction == "outbound",
    )
    messages_sent = await count(
        Message,
        Message.organization_id == org_id,
        Message.direction == "outbound",
        Message.status == "sent",
    )
    meetings_booked = await count(
        Appointment,
        Appointment.organization_id == org_id,
        Appointment.status.in_(("scheduled", "confirmed", "booked")),
    )
    total_companies = await count(Company, Company.organization_id == org_id)

    integration_status = await get_settings_status(current_user, db)
    integrations = {
        item.id: {
            "provider": item.provider,
            "status": item.status,
            "name": item.name,
        }
        for item in integration_status.integrations
    }
    rates = {
        "qualification_rate": round(qualified_leads / total_leads * 100, 1)
        if total_leads else 0.0,
        "outreach_dispatch_rate": round(messages_sent / outbound_messages * 100, 1)
        if outbound_messages else 0.0,
        "meeting_conversion_rate": round(meetings_booked / messages_sent * 100, 1)
        if messages_sent else 0.0,
    }

    return {
        "funnel": [
            {"stage": "Discovered Leads", "count": total_leads, "color": "#0ea5e9"},
            {"stage": "Leads with Decision Makers", "count": enriched_leads, "color": "#38bdf8"},
            {"stage": "Qualified Leads (Score ≥ 70)", "count": qualified_leads, "color": "#10b981"},
            {"stage": "Outbound Messages", "count": outbound_messages, "color": "#6366f1"},
            {"stage": "Delivered Messages", "count": messages_sent, "color": "#8b5cf6"},
            {"stage": "Booked Meetings", "count": meetings_booked, "color": "#ec4899"},
        ],
        "score_distribution": {
            "high_priority": high_priority_leads,
            "qualified": max(0, qualified_leads - high_priority_leads),
            "nurture": nurture_leads,
            "disqualified": disqualified_leads,
            "unscored": unscored_leads,
        },
        "rates": rates,
        "rate_counts": {
            "qualification_rate": {
                "numerator": qualified_leads,
                "denominator": total_leads,
            },
            "outreach_dispatch_rate": {
                "numerator": messages_sent,
                "denominator": outbound_messages,
            },
            "meeting_conversion_rate": {
                "numerator": meetings_booked,
                "denominator": messages_sent,
            },
        },
        "rate_definitions": {
            "qualification_rate": "Qualified leads (score >= 70) / all organization leads.",
            "outreach_dispatch_rate": "Sent outbound messages / all outbound messages.",
            "meeting_conversion_rate": "Scheduled, confirmed, or booked appointments / sent outbound messages.",
        },
        "data_scope": "Live counts scoped to the authenticated organization; rates use the numerators and denominators returned.",
        "integrations_status": integrations,
        "total_companies": total_companies,
    }
