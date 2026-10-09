"""LangGraph nodes for the Enforcer workflow."""

import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.agents.enforcer.state import EnforcerState
from app.services.policy_service import PolicyService
from app.services.outreach_service import OutreachService
from app.services.message_event_service import MessageEventService
from app.services.followup_service import FollowupService
from app.models.message import Message
from app.models.lead import Lead
from app.models.person import Person
from app.models.campaign_lead import CampaignLead

logger = logging.getLogger(__name__)

async def load_message(state: EnforcerState, db: AsyncSession) -> dict:
    """Load all necessary DB models for execution."""
    msg_id = state.get("message_id")
    if not msg_id:
        return {"errors": ["Missing message_id"], "status": "failed"}
        
    res = await db.execute(
        select(Message)
        .options(
            selectinload(Message.lead).selectinload(Lead.person).selectinload(Person.contacts),
            selectinload(Message.campaign)
        )
        .where(Message.id == msg_id)
    )
    msg = res.scalars().first()
    
    if not msg:
        return {"errors": [f"Message {msg_id} not found"], "status": "failed"}
        
    res_cl = await db.execute(
        select(CampaignLead)
        .where(CampaignLead.campaign_id == msg.campaign_id, CampaignLead.lead_id == msg.lead_id)
    )
    cl = res_cl.scalars().first()
        
    return {
        "message": msg,
        "lead": msg.lead,
        "campaign": msg.campaign,
        "campaign_lead": cl
    }


async def evaluate_policy(state: EnforcerState, policy_service: PolicyService) -> dict:
    """Run business rules to check if sending is permitted."""
    if "errors" in state and state["errors"]: return {}
    
    msg = state["message"]
    result = await policy_service.evaluate(msg, state["lead"], state["campaign"])
    
    if not result.allowed:
        logger.warning(f"Message {msg.id} blocked by policy: {result.reasons}")
        
    return {"policy_result": result}


async def execute_send(state: EnforcerState, outreach_service: OutreachService) -> dict:
    """Actually send the message if policy allows it."""
    if "errors" in state and state["errors"]: return {}
    
    policy = state.get("policy_result")
    if not policy or not policy.allowed:
        return {"status": "blocked"}
        
    msg = state["message"]
    lead = state["lead"]
    
    email = next((c.value for c in lead.person.contacts if c.type == "email"), None)
    
    try:
        ext_id = await outreach_service.send_message(msg, email)
        return {"send_result_external_id": ext_id, "status": "sent"}
    except Exception as e:
        return {"errors": [f"Send failed: {e}"], "status": "failed"}


async def record_event(state: EnforcerState, event_service: MessageEventService) -> dict:
    """Record audit trail events for what happened."""
    if not state.get("message"): return {}
    
    msg = state["message"]
    policy = state.get("policy_result")
    
    if not policy or not policy.allowed:
        reasons = policy.reasons if policy else ["Unknown policy check failure"]
        await event_service.record_event(msg.id, "MESSAGE_BLOCKED", {"reasons": reasons})
        return {"event_recorded": True}
        
    if state.get("status") == "sent":
        await event_service.record_event(msg.id, "MESSAGE_SENT", {"external_id": state["send_result_external_id"]})
    elif state.get("status") == "failed":
        await event_service.record_event(msg.id, "MESSAGE_FAILED", {"errors": state.get("errors")})
        
    return {"event_recorded": True}
    

async def schedule_followup(state: EnforcerState, followup_service: FollowupService) -> dict:
    """Schedule the next sequence step if sending succeeded."""
    if state.get("status") != "sent": return {}
    
    if not state.get("campaign_lead"): return {}
    
    scheduled = await followup_service.schedule_followup(state["message"], state["campaign_lead"])
    return {"followup_scheduled": scheduled}
