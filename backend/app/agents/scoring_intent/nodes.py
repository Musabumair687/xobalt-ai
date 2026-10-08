"""LangGraph nodes for the Scoring and Intent workflow."""

import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.agents.scoring_intent.state import ScoringIntentState
from app.services.intent_service import IntentService
from app.services.intent_signal_service import IntentSignalService
from app.services.scoring_service import ScoringService, classify_score
from app.models.lead import Lead
from app.models.company_intelligence import CompanyIntelligence

logger = logging.getLogger(__name__)

async def load_context(state: ScoringIntentState, db: AsyncSession) -> dict:
    """Load the Lead, Company, Person, Intelligence, and existing signals from DB."""
    lead_id = state.get("lead_id")
    if not lead_id:
        return {"errors": ["No lead_id provided"]}

    # Load lead with relationships
    result = await db.execute(
        select(Lead)
        .options(
            selectinload(Lead.company),
            selectinload(Lead.person)
        )
        .where(Lead.id == lead_id)
    )
    lead = result.scalars().first()
    
    if not lead:
        return {"errors": [f"Lead {lead_id} not found"]}

    # Load intelligence
    intelligence = None
    if lead.company_id:
        intel_result = await db.execute(
            select(CompanyIntelligence).where(CompanyIntelligence.company_id == lead.company_id)
        )
        intelligence = intel_result.scalars().first()

    # Load existing signals
    signal_service = IntentSignalService(db)
    existing_signals = await signal_service.get_signals_for_lead(lead_id)

    return {
        "lead": lead,
        "company": lead.company,
        "person": lead.person,
        "intelligence": intelligence,
        "existing_signals": list(existing_signals)
    }

async def detect_intent(state: ScoringIntentState, intent_service: IntentService) -> dict:
    """Analyze website intelligence for new intent signals."""
    if "errors" in state and state["errors"]:
        return {}
        
    intelligence = state.get("intelligence")
    if not intelligence:
        return {"detected_intent_signals": []}

    signals = await intent_service.detect_intent(intelligence)
    return {"detected_intent_signals": signals}

async def validate_intent(state: ScoringIntentState, signal_service: IntentSignalService) -> dict:
    """Validate and save newly detected signals to the database."""
    if "errors" in state and state["errors"]:
        return {}

    detected = state.get("detected_intent_signals", [])
    if not detected:
        return {"validated_intent_signals": state.get("existing_signals", [])}

    lead_id = state["lead_id"]
    added_signals = await signal_service.add_signals(lead_id, detected)
    
    # Combine old and new
    all_signals = state.get("existing_signals", []) + added_signals
    return {"validated_intent_signals": all_signals}

async def calculate_score(state: ScoringIntentState, scoring_service: ScoringService) -> dict:
    """Calculate the final lead score deterministically."""
    if "errors" in state and state["errors"]:
        return {}

    company = state.get("company")
    person = state.get("person")
    intelligence = state.get("intelligence")
    signals = state.get("validated_intent_signals", [])

    breakdown = scoring_service.score_lead(company, person, intelligence, signals)
    total_score = breakdown.total_score()
    
    return {
        "score_breakdown": breakdown,
        "total_score": total_score
    }

async def classify_lead(state: ScoringIntentState) -> dict:
    """Classify the lead based on its score."""
    if "errors" in state and state["errors"]:
        return {}

    score = state.get("total_score", 0)
    classification = classify_score(score)
    return {"classification": classification}

async def store_result(state: ScoringIntentState, db: AsyncSession) -> dict:
    """Save the final score and classification to the Lead record."""
    if "errors" in state and state["errors"]:
        return {}

    lead = state.get("lead")
    if not lead:
        return {}

    lead.score = state["total_score"]
    lead.qualification_status = state["classification"].lower()
    
    # Store breakdown in metadata_ (not overwriting other metadata if possible)
    current_meta = lead.metadata_ or {}
    current_meta["score_breakdown"] = state["score_breakdown"].model_dump()
    lead.metadata_ = current_meta

    await db.commit()
    return {}
