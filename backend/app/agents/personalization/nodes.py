"""LangGraph nodes for the Personalization workflow."""

import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.agents.personalization.state import PersonalizationState
from app.services.personalization_service import PersonalizationService
from app.services.message_validation_service import MessageValidationService
from app.models.lead import Lead
from app.models.campaign import Campaign
from app.models.company_intelligence import CompanyIntelligence
from app.models.intent_signal import IntentSignal
from app.models.message import Message

logger = logging.getLogger(__name__)


async def load_context(state: PersonalizationState, db: AsyncSession) -> dict:
    """Load the Lead, Campaign, and all context from DB."""
    lead_id = state.get("lead_id")
    campaign_id = state.get("campaign_id")
    
    if not lead_id or not campaign_id:
        return {"errors": ["Missing lead_id or campaign_id"]}

    # Load Campaign
    res_camp = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    campaign = res_camp.scalars().first()
    if not campaign:
        return {"errors": [f"Campaign {campaign_id} not found"]}

    # Load Lead and relations
    res_lead = await db.execute(
        select(Lead)
        .options(selectinload(Lead.company), selectinload(Lead.person))
        .where(Lead.id == lead_id)
    )
    lead = res_lead.scalars().first()
    if not lead:
        return {"errors": [f"Lead {lead_id} not found"]}

    # Load Intelligence
    intel = None
    if lead.company_id:
        res_intel = await db.execute(
            select(CompanyIntelligence).where(CompanyIntelligence.company_id == lead.company_id)
        )
        intel = res_intel.scalars().first()

    # Load Intent Signals
    res_signals = await db.execute(
        select(IntentSignal)
        .where(IntentSignal.lead_id == lead_id)
        .order_by(IntentSignal.confidence.desc())
    )
    signals = list(res_signals.scalars().all())

    return {
        "lead": lead,
        "campaign": campaign,
        "company": lead.company,
        "person": lead.person,
        "intelligence": intel,
        "intent_signals": signals
    }


async def build_personalization_context(state: PersonalizationState, personalization_service: PersonalizationService) -> dict:
    """Format DB context into a string for the LLM."""
    if "errors" in state and state["errors"]:
        return {}
        
    context_str = personalization_service.build_context_string(
        company=state.get("company"),
        person=state.get("person"),
        intelligence=state.get("intelligence"),
        intent_signals=state.get("intent_signals", []),
        campaign=state.get("campaign")
    )
    return {"personalization_context": context_str}


async def generate_message(state: PersonalizationState, personalization_service: PersonalizationService) -> dict:
    """Call the LLM to generate the message components."""
    if "errors" in state and state["errors"]:
        return {}
        
    ctx = state.get("personalization_context", "")
    msg = await personalization_service.generate_message(ctx)
    
    if not msg:
        return {"errors": ["LLM generation failed or returned empty"]}
        
    return {"generated_message": msg}


async def validate_message(state: PersonalizationState, validation_service: MessageValidationService) -> dict:
    """Deterministically validate the generated message."""
    if "errors" in state and state["errors"]:
        return {}
        
    msg = state.get("generated_message")
    if not msg:
        return {"errors": ["No generated message to validate"]}
        
    result = validation_service.validate(msg)
    
    status = "pending_approval" if result.is_valid else "draft"
    
    return {
        "validation_result": result,
        "approval_status": status,
        "errors": state.get("errors", []) + result.errors,
        "warnings": state.get("warnings", []) + result.warnings
    }


async def store_message(state: PersonalizationState, db: AsyncSession) -> dict:
    """Save the message to the DB for human approval."""
    if not state.get("lead") or not state.get("campaign"):
        return {}
        
    # We still save it even if invalid, so human can see and fix it, or we see why it failed.
    msg_data = state.get("generated_message")
    
    if msg_data:
        full_body = f"Hi {state.get('person').first_name if state.get('person') else 'there'},\n\n"
        full_body += f"{msg_data.opening}\n\n{msg_data.value_proposition}\n\n{msg_data.cta}"
        subject = msg_data.subject
    else:
        full_body = ""
        subject = ""
        
    status = state.get("approval_status", "draft")
        
    # Check if a pending message already exists to avoid duplicates
    res_existing = await db.execute(
        select(Message).where(
            Message.lead_id == state["lead"].id,
            Message.campaign_id == state["campaign"].id,
            Message.status.in_(["draft", "pending_approval"])
        )
    )
    existing = res_existing.scalars().first()
    
    if existing:
        existing.subject = subject
        existing.body = full_body
        existing.status = status
        db.add(existing)
        message_id = existing.id
    else:
        new_msg = Message(
            organization_id=state["campaign"].organization_id,
            lead_id=state["lead"].id,
            campaign_id=state["campaign"].id,
            channel="email",
            direction="outbound",
            subject=subject,
            body=full_body,
            status=status
        )
        db.add(new_msg)
        await db.flush()
        message_id = new_msg.id
        
    await db.commit()
    
    return {"message_id": message_id}
