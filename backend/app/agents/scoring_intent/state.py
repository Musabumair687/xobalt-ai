"""State definition for the Scoring and Intent workflow."""

import uuid
from typing import TypedDict, Any
from app.models.lead import Lead
from app.models.company import Company
from app.models.person import Person
from app.models.company_intelligence import CompanyIntelligence
from app.models.intent_signal import IntentSignal
from app.schemas.scoring import ScoreBreakdown

class ScoringIntentState(TypedDict, total=False):
    """The state dictionary travelling through the Scoring/Intent LangGraph."""
    lead_id: uuid.UUID
    
    # Context loaded from DB
    lead: Lead
    company: Company | None
    person: Person | None
    intelligence: CompanyIntelligence | None
    existing_signals: list[IntentSignal]
    
    # Intermediary outputs
    detected_intent_signals: list[dict]
    validated_intent_signals: list[IntentSignal]
    
    # Final outputs
    score_breakdown: ScoreBreakdown
    total_score: int
    classification: str
    
    # Telemetry
    errors: list[str]
    warnings: list[str]
