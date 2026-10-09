"""Pydantic schemas for Phase 7 Enforcer."""

import uuid
from typing import Optional, List
from pydantic import BaseModel, Field

class PolicyResult(BaseModel):
    """Result of evaluating a message against outbound policies."""
    allowed: bool
    reasons: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

class EnforcerRequest(BaseModel):
    """Request to process a message through the Enforcer workflow."""
    message_id: uuid.UUID
    
class EnforcerResult(BaseModel):
    """Result of the Enforcer execution for a given message."""
    message_id: uuid.UUID
    status: str
    policy_result: Optional[PolicyResult] = None
    event_recorded: bool = False
    followup_scheduled: bool = False
    errors: List[str] = Field(default_factory=list)
