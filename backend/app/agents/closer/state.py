"""State definition for Closer workflow."""

import uuid
from typing import TypedDict, Optional, List
from app.models.conversation import Conversation
from app.models.conversation_message import ConversationMessage
from app.models.lead import Lead
from app.models.campaign import Campaign
from app.schemas.closer import ReplyClassification

class CloserState(TypedDict, total=False):
    """State for the Phase 8 Closer execution graph."""
    conversation_message_id: uuid.UUID
    
    # DB Models
    latest_message: Optional[ConversationMessage]
    conversation: Optional[Conversation]
    messages: List[ConversationMessage]
    lead: Optional[Lead]
    campaign: Optional[Campaign]
    
    # Context & Classification
    context_string: str
    classification: Optional[ReplyClassification]
    
    # Execution decisions
    action_taken: str
    draft_response: Optional[str]
    response_generated: bool
    validation_status: Optional[str]
    
    # Global output
    errors: list[str]
