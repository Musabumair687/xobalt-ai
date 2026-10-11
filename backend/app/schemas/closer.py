"""Pydantic schemas for Phase 8 Closer."""

import uuid
from typing import Optional, List
from pydantic import BaseModel, Field

class ReplyClassification(BaseModel):
    """Result of classifying a prospect's reply."""
    intent: str = Field(description="One of: INTERESTED, QUESTION, PRICING, NOT_INTERESTED, LATER, UNSUBSCRIBE, OUT_OF_OFFICE, UNCLEAR")
    confidence: float = Field(description="Confidence score between 0.0 and 1.0")
    reason: str = Field(description="Explanation of why this intent was chosen")
    
class CloserRequest(BaseModel):
    """Request to process a reply message through the Closer workflow."""
    conversation_message_id: uuid.UUID
    
class CloserResult(BaseModel):
    """Result of the Closer execution for a given reply."""
    conversation_message_id: uuid.UUID
    intent: str
    confidence: float
    action_taken: str
    response_generated: bool = False
    validation_status: Optional[str] = None
    errors: List[str] = Field(default_factory=list)
