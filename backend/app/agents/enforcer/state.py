"""State definition for Enforcer workflow."""

import uuid
from typing import TypedDict, Optional
from app.models.message import Message
from app.models.lead import Lead
from app.models.campaign import Campaign
from app.models.campaign_lead import CampaignLead
from app.schemas.enforcer import PolicyResult

class EnforcerState(TypedDict, total=False):
    """State for the Phase 7 Enforcer execution graph."""
    message_id: uuid.UUID
    
    # DB Models
    message: Optional[Message]
    lead: Optional[Lead]
    campaign: Optional[Campaign]
    campaign_lead: Optional[CampaignLead]
    
    # Policy Evaluation
    policy_result: Optional[PolicyResult]
    
    # Execution
    send_result_external_id: Optional[str]
    event_recorded: bool
    followup_scheduled: bool
    
    # Global output
    status: str
    errors: list[str]
