"""API router for Campaigns and Enforcer Execution."""

import uuid
import logging
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.dependencies import get_db
from app.schemas.enforcer import EnforcerRequest, EnforcerResult
from app.services.campaign_service import CampaignService
from app.services.policy_service import PolicyService
from app.services.outreach_service import OutreachService
from app.services.message_event_service import MessageEventService
from app.services.followup_service import FollowupService
from app.integrations.email.gmail import GmailProvider
from app.workflows.enforcer_workflow import build_enforcer_graph

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/campaigns", tags=["Campaigns & Enforcer"])

from pydantic import BaseModel, Field
from typing import Optional, List
from sqlalchemy import select, func, desc
from sqlalchemy.orm import selectinload
from app.models.campaign import Campaign
from app.models.lead import Lead
from app.models.message import Message
from app.models.organization import Organization

class CreateCampaignRequest(BaseModel):
    name: str = Field(..., examples=["Q4 Real Estate Growth"])
    target_industry: str = Field(default="Real Estate")
    offer: Optional[str] = Field(default="Automated AI pipeline for client acquisition")
    daily_limit: int = Field(default=30, ge=1, le=500)
    description: Optional[str] = None

@router.get("", summary="List all campaigns with live lead and message metrics")
async def list_campaigns(db: AsyncSession = Depends(get_db)):
    """Fetch all campaigns with total enrolled leads and sent messages."""
    stmt = select(Campaign).order_by(desc(Campaign.created_at))
    res = await db.execute(stmt)
    campaigns = res.scalars().all()

    output = []
    for c in campaigns:
        # Count leads enrolled in this campaign or industry
        leads_res = await db.execute(
            select(func.count(Lead.id))
            .join(Lead.company)
            .where(Lead.company.has(industry=c.target_industry))
        )
        lead_count = leads_res.scalar() or 0

        # Count messages for this campaign
        msg_res = await db.execute(
            select(func.count(Message.id)).where(Message.campaign_id == c.id)
        )
        message_count = msg_res.scalar() or 0

        sent_res = await db.execute(
            select(func.count(Message.id))
            .where(Message.campaign_id == c.id, Message.status == "sent")
        )
        sent_count = sent_res.scalar() or 0

        output.append({
            "id": str(c.id),
            "name": c.name,
            "description": c.description,
            "status": c.status,
            "target_industry": c.target_industry,
            "daily_limit": c.daily_limit,
            "settings": c.settings or {},
            "lead_count": lead_count,
            "message_count": message_count,
            "sent_count": sent_count,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        })
    return output

@router.post("", status_code=status.HTTP_201_CREATED, summary="Create a new outbound campaign")
async def create_campaign(
    payload: CreateCampaignRequest,
    db: AsyncSession = Depends(get_db)
):
    """Create a new campaign targeting a specific industry."""
    org_res = await db.execute(select(Organization).limit(1))
    org = org_res.scalars().first()
    if not org:
        org = Organization(name="Default Workspace", slug="default-workspace")
        db.add(org)
        await db.flush()

    new_camp = Campaign(
        organization_id=org.id,
        name=payload.name,
        target_industry=payload.target_industry,
        description=payload.description,
        daily_limit=payload.daily_limit,
        status="active",
        settings={"offer": payload.offer or ""}
    )
    db.add(new_camp)
    await db.commit()
    await db.refresh(new_camp)

    return {
        "id": str(new_camp.id),
        "name": new_camp.name,
        "target_industry": new_camp.target_industry,
        "status": new_camp.status,
        "daily_limit": new_camp.daily_limit,
        "settings": new_camp.settings,
        "created_at": new_camp.created_at.isoformat() if new_camp.created_at else None,
    }


@router.post(
    "/{campaign_id}/execute",
    status_code=status.HTTP_202_ACCEPTED
)
async def execute_campaign(
    campaign_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Trigger the background worker to process all approved messages for a campaign."""
    # In a real app we'd enqueue to Redis/Celery. For now we use FastAPI BackgroundTasks
    # But since the background task needs a new DB session, we will just use the campaign service
    # Wait, FastAPI BackgroundTasks can't safely share the request's DB session if it closes.
    # For Phase 7 API simulation, let's just trigger it directly in the foreground or assume 
    # the frontend calls the Enforcer endpoint for specific messages.
    
    # We will just run it synchronously for simplicity in this phase
    svc = CampaignService(db)
    await svc.process_campaign_outreach(campaign_id)
    
    return {"status": "Execution started", "campaign_id": campaign_id}

@router.post(
    "/enforcer/execute_message",
    response_model=EnforcerResult
)
async def execute_single_message(
    request: EnforcerRequest,
    db: AsyncSession = Depends(get_db)
):
    """Run a single message through the Enforcer workflow (useful for testing/UI)."""
    policy_svc = PolicyService(db)
    email_provider = GmailProvider()
    outreach_svc = OutreachService(db, email_provider)
    event_svc = MessageEventService(db)
    followup_svc = FollowupService(db)
    
    graph = build_enforcer_graph(db, policy_svc, outreach_svc, event_svc, followup_svc)
    
    initial_state = {"message_id": request.message_id, "errors": []}
    
    try:
        final_state = await graph.ainvoke(initial_state)
        return EnforcerResult(
            message_id=request.message_id,
            status=final_state.get("status", "unknown"),
            policy_result=final_state.get("policy_result"),
            event_recorded=final_state.get("event_recorded", False),
            followup_scheduled=final_state.get("followup_scheduled", False),
            errors=final_state.get("errors", [])
        )
    except Exception as e:
        logger.error(f"Error executing enforcer: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
