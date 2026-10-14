"""API router for Campaigns and Enforcer Execution."""

import uuid
import logging
from datetime import datetime, timezone
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.dependencies import get_db
from app.schemas.enforcer import EnforcerRequest, EnforcerResult
from app.services.policy_service import PolicyService
from app.services.outreach_service import OutreachService
from app.services.message_event_service import MessageEventService
from app.services.followup_service import FollowupService
from app.integrations.email import get_email_provider
from app.workflows.enforcer_workflow import build_enforcer_graph
from app.integrations.provider_errors import safe_provider_error
from app.models.agent_run import AgentRun
from app.workers.campaign_tasks import CAMPAIGN_TASK_NAME

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/campaigns", tags=["Campaigns & Enforcer"])

from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy import select, func, desc
from app.models.campaign import Campaign
from app.models.lead import Lead
from app.models.message import Message
from app.models.company import Company
from app.models.user import User
from app.auth import get_current_user
from app.workers.celery_app import celery_app
from app.schemas.common import PaginatedResponse
from app.schemas.contracts import CampaignListItem
from app.services.integration_settings_service import organization_settings_scope

class CreateCampaignRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, examples=["Q4 Real Estate Growth"])
    target_industry: str = Field(default="Real Estate", min_length=1, max_length=255)
    offer: Optional[str] = Field(default="Automated AI pipeline for client acquisition", max_length=5000)
    daily_limit: int = Field(default=30, ge=1, le=500)
    description: Optional[str] = Field(default=None, max_length=10000)

@router.get(
    "",
    response_model=PaginatedResponse[CampaignListItem],
    summary="List campaigns with live lead and message metrics",
)
async def list_campaigns(
    current_user: User = Depends(get_current_user),
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    db: AsyncSession = Depends(get_db),
):
    """Fetch one page of campaigns with total enrolled leads and sent messages."""
    stmt = (
        select(Campaign)
        .where(Campaign.organization_id == current_user.organization_id)
        .order_by(desc(Campaign.created_at))
    )
    total = await db.scalar(
        select(func.count()).select_from(stmt.order_by(None).subquery())
    ) or 0
    res = await db.execute(stmt.offset((page - 1) * page_size).limit(page_size))
    campaigns = res.scalars().all()

    output = []
    for c in campaigns:
        # Count leads enrolled in this campaign or industry
        leads_res = await db.execute(
            select(func.count(Lead.id))
            .join(Lead.company)
            .where(
                Lead.organization_id == current_user.organization_id,
                Company.organization_id == current_user.organization_id,
                Company.industry == c.target_industry,
            )
        )
        lead_count = leads_res.scalar() or 0

        # Count messages for this campaign
        msg_res = await db.execute(
            select(func.count(Message.id)).where(
                Message.campaign_id == c.id,
                Message.organization_id == current_user.organization_id,
            )
        )
        message_count = msg_res.scalar() or 0

        sent_res = await db.execute(
            select(func.count(Message.id))
            .where(
                Message.campaign_id == c.id,
                Message.organization_id == current_user.organization_id,
                Message.status == "sent",
            )
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
    return {
        "items": output,
        "page": page,
        "page_size": page_size,
        "total": total,
        "pages": (total + page_size - 1) // page_size,
    }

@router.post("", status_code=status.HTTP_201_CREATED, summary="Create a new outbound campaign")
async def create_campaign(
    payload: CreateCampaignRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new campaign targeting a specific industry."""
    new_camp = Campaign(
        organization_id=current_user.organization_id,
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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Queue campaign delivery and return a durable execution identifier."""
    campaign_res = await db.execute(
        select(Campaign).where(
            Campaign.id == campaign_id,
            Campaign.organization_id == current_user.organization_id,
        )
    )
    campaign = campaign_res.scalars().first()
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")

    run = AgentRun(
        id=uuid.uuid4(),
        organization_id=current_user.organization_id,
        agent_type="campaign_execution",
        status="queued",
        started_at=datetime.now(timezone.utc),
        input_data={"campaign_id": str(campaign_id)},
        output_data={"selected": 0, "sent": 0, "blocked": 0, "failed": 0, "skipped": 0},
        triggered_by=str(current_user.id),
    )
    db.add(run)
    await db.commit()

    try:
        celery_app.send_task(
            CAMPAIGN_TASK_NAME,
            args=[str(run.id), str(campaign_id), str(current_user.organization_id)],
            task_id=str(run.id),
            retry=False,
        )
    except Exception as exc:
        safe_error = safe_provider_error("campaign_queue", exc)
        run.status = "failed"
        run.error_message = str(safe_error)
        run.completed_at = datetime.now(timezone.utc)
        run.duration_seconds = 0
        await db.commit()
        logger.error("Could not enqueue campaign run %s (%s).", run.id, safe_error.error_type)
        raise HTTPException(
            status_code=503,
            detail="Campaign worker queue is unavailable; execution was not started.",
        ) from exc

    return {
        "run_id": str(run.id),
        "campaign_id": str(campaign.id),
        "status": "queued",
    }


@router.get("/executions/{run_id}", summary="Get campaign execution status")
async def get_campaign_execution_status(
    run_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    run_result = await db.execute(
        select(AgentRun).where(
            AgentRun.id == run_id,
            AgentRun.organization_id == current_user.organization_id,
            AgentRun.agent_type == "campaign_execution",
        )
    )
    run = run_result.scalars().first()
    if run is None:
        raise HTTPException(status_code=404, detail="Campaign execution not found")
    return {
        "run_id": str(run.id),
        "campaign_id": (run.input_data or {}).get("campaign_id"),
        "status": run.status,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "duration_seconds": run.duration_seconds,
        "output": run.output_data or {},
        "error": run.error_message,
    }

@router.post(
    "/enforcer/execute_message",
    response_model=EnforcerResult
)
async def execute_single_message(
    request: EnforcerRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Run a single message through the Enforcer workflow (useful for testing/UI)."""
    msg_res = await db.execute(
        select(Message)
        .join(Campaign, Campaign.id == Message.campaign_id)
        .join(Lead, Lead.id == Message.lead_id)
        .where(
            Message.id == request.message_id,
            Message.organization_id == current_user.organization_id,
            Campaign.organization_id == current_user.organization_id,
            Lead.organization_id == current_user.organization_id,
        )
    )
    message = msg_res.scalars().first()
    if message is None:
        raise HTTPException(status_code=404, detail="Message not found")
    if message.status != "approved":
        raise HTTPException(
            status_code=409,
            detail="Message must be explicitly approved before execution.",
        )
    if message.direction != "outbound" or message.channel != "email":
        raise HTTPException(
            status_code=409,
            detail="Only approved outbound email messages can be executed.",
        )

    try:
        async with organization_settings_scope(db, current_user.organization_id):
            policy_svc = PolicyService(db)
            email_provider = get_email_provider()
            outreach_svc = OutreachService(db, email_provider)
            event_svc = MessageEventService(db)
            followup_svc = FollowupService(db)
            graph = build_enforcer_graph(
                db,
                policy_svc,
                outreach_svc,
                event_svc,
                followup_svc,
            )
            final_state = await graph.ainvoke(
                {"message_id": request.message_id, "errors": []}
            )
        return EnforcerResult(
            message_id=request.message_id,
            status=final_state.get("status", "unknown"),
            policy_result=final_state.get("policy_result"),
            event_recorded=final_state.get("event_recorded", False),
            followup_scheduled=final_state.get("followup_scheduled", False),
            errors=final_state.get("errors", [])
        )
    except Exception as e:
        safe_error = safe_provider_error("message_execution", e)
        logger.error("Enforcer execution failed (%s).", safe_error.error_type)
        raise HTTPException(status_code=500, detail=str(safe_error)) from e
