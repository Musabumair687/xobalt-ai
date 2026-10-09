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
