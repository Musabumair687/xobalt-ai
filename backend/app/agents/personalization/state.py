"""State definition for the Personalization workflow."""

import uuid
from typing import TypedDict, Any, List
from app.models.lead import Lead
from app.models.company import Company
from app.models.person import Person
from app.models.company_intelligence import CompanyIntelligence
from app.models.intent_signal import IntentSignal
from app.models.campaign import Campaign
from app.schemas.personalization import GeneratedMessage, MessageValidationResult

class PersonalizationState(TypedDict, total=False):
    """The state dictionary travelling through the Personalization LangGraph."""
    lead_id: uuid.UUID
    campaign_id: uuid.UUID
    
    # Context loaded from DB
    lead: Lead | None
    campaign: Campaign | None
    company: Company | None
    person: Person | None
    intelligence: CompanyIntelligence | None
    intent_signals: List[IntentSignal]
    
    # Text context
    personalization_context: str
    
    # Outputs
    generated_message: GeneratedMessage | None
    validation_result: MessageValidationResult | None
    
    # DB State
    message_id: uuid.UUID | None
    approval_status: str | None
    
    # Telemetry
    errors: list[str]
    warnings: list[str]
