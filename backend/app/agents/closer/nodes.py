"""LangGraph nodes for the Closer workflow."""

import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.agents.closer.state import CloserState
from app.services.conversation_context_service import ConversationContextService
from app.services.reply_classification_service import ReplyClassificationService
from app.services.response_service import ResponseService
from app.models.conversation_message import ConversationMessage
from app.models.conversation import Conversation
from app.models.lead import Lead
from app.models.campaign_lead import CampaignLead
from app.models.campaign import Campaign
from app.models.person import Person
from app.models.company import Company
from app.models.contact import Contact

logger = logging.getLogger(__name__)

async def load_conversation(state: CloserState, db: AsyncSession) -> dict:
    """Load all necessary DB models for execution."""
    msg_id = state.get("conversation_message_id")
    if not msg_id:
        return {"errors": ["Missing conversation_message_id"], "action_taken": "ERROR"}
        
    res_msg = await db.execute(
        select(ConversationMessage)
        .options(
            selectinload(ConversationMessage.conversation)
            .selectinload(Conversation.lead)
            .selectinload(Lead.person)
            .selectinload(Person.contacts),
            selectinload(ConversationMessage.conversation)
            .selectinload(Conversation.lead)
            .selectinload(Lead.company)
        )
        .where(ConversationMessage.id == msg_id)
    )
    msg = res_msg.scalars().first()
    
    if not msg:
        return {"errors": [f"ConversationMessage {msg_id} not found"], "action_taken": "ERROR"}
        
    res_history = await db.execute(
        select(ConversationMessage)
        .where(ConversationMessage.conversation_id == msg.conversation_id)
        .order_by(ConversationMessage.sequence_number.asc())
    )
    history = list(res_history.scalars().all())
    
    # Load campaign
    res_cl = await db.execute(
        select(CampaignLead)
        .options(selectinload(CampaignLead.campaign))
        .where(CampaignLead.lead_id == msg.conversation.lead_id)
    )
    cl = res_cl.scalars().first()
    campaign = cl.campaign if cl else None
        
    return {
        "latest_message": msg,
        "conversation": msg.conversation,
        "messages": history,
        "lead": msg.conversation.lead,
        "campaign": campaign
    }


async def build_context(state: CloserState, context_service: ConversationContextService) -> dict:
    """Build the context string for the LLM."""
    if state.get("errors"): return {}
    
    context_str = context_service.build_context(
        state["conversation"],
        state["messages"],
        state["lead"],
        state["campaign"]
    )
    return {"context_string": context_str}


async def classify_intent(state: CloserState, classification_service: ReplyClassificationService) -> dict:
    """Run LLM classification."""
    if state.get("errors"): return {}
    
    cls_result = await classification_service.classify(state["context_string"])
    if not cls_result:
        return {"errors": ["Classification failed"], "action_taken": "ERROR"}
        
    # Example confidence check logic
    if cls_result.confidence < 0.60:
        cls_result.intent = "UNCLEAR" # Force human review
        
    return {"classification": cls_result}


def route_action(state: CloserState) -> str:
    """Conditional edge router based on intent."""
    if state.get("errors"):
        return "end"
        
    intent = state.get("classification").intent
    
    if intent in ["QUESTION", "PRICING"]:
        return "generate_response"
    elif intent == "INTERESTED":
        return "route_to_booking"
    elif intent == "UNSUBSCRIBE":
        return "mark_opt_out"
    elif intent == "NOT_INTERESTED":
        return "stop_campaign"
    elif intent == "LATER":
        return "schedule_later"
    elif intent == "OUT_OF_OFFICE":
        return "wait"
    else: # UNCLEAR
        return "human_review"

# Action Nodes

async def generate_response(state: CloserState, response_service: ResponseService, db: AsyncSession) -> dict:
    """Generate response for QUESTION or PRICING."""
    intent = state.get("classification").intent
    draft = await response_service.generate_response(state["context_string"], intent)
    
    # Store draft for human review conceptually (could be stored as a Draft Message in DB)
    state["conversation"].status = "WAITING_FOR_HUMAN_APPROVAL"
    await db.commit()
    
    return {"draft_response": draft, "response_generated": True, "action_taken": "GENERATED_RESPONSE_PENDING_APPROVAL"}

async def route_to_booking(state: CloserState, db: AsyncSession) -> dict:
    state["conversation"].status = "BOOKING"
    await db.commit()
    return {"action_taken": "ROUTED_TO_BOOKING"}

async def mark_opt_out(state: CloserState, db: AsyncSession) -> dict:
    lead = state["lead"]
    if lead.person:
        meta = lead.person.metadata_ or {}
        meta["opted_out"] = True
        lead.person.metadata_ = meta
    state["conversation"].status = "OPTED_OUT"
    await db.commit()
    return {"action_taken": "OPTED_OUT"}

async def stop_campaign(state: CloserState, db: AsyncSession) -> dict:
    state["conversation"].status = "NOT_INTERESTED"
    await db.commit()
    return {"action_taken": "STOPPED_CAMPAIGN"}

async def schedule_later(state: CloserState, db: AsyncSession) -> dict:
    state["conversation"].status = "LATER"
    await db.commit()
    return {"action_taken": "SCHEDULED_LATER"}

async def wait_ooo(state: CloserState, db: AsyncSession) -> dict:
    # Just wait, don't change state much
    return {"action_taken": "WAITING_FOR_RETURN"}

async def human_review(state: CloserState, db: AsyncSession) -> dict:
    state["conversation"].status = "WAITING_FOR_HUMAN_APPROVAL"
    await db.commit()
    return {"action_taken": "ESCALATED_TO_HUMAN"}
