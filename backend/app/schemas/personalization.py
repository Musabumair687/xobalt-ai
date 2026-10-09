"""Pydantic schemas for Phase 6 Personalization and Human Approval."""

from __future__ import annotations
import uuid
from typing import Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Core Generation Output
# ---------------------------------------------------------------------------

class GeneratedMessage(BaseModel):
    """The structured output required from the LLM during personalization."""
    subject: str = Field(description="Email subject line.")
    opening: str = Field(description="The first sentence or two hooking the lead.")
    value_proposition: str = Field(description="How our offer solves their specific problem.")
    cta: str = Field(description="The Call To Action.")

# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

class MessageValidationResult(BaseModel):
    """Deterministic validation of a generated message."""
    is_valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

# ---------------------------------------------------------------------------
# Approval Flow
# ---------------------------------------------------------------------------

class ApprovalRequest(BaseModel):
    """Request to approve or reject a generated message."""
    action: str = Field(..., description="'approve', 'reject', 'regenerate', or 'edit'")
    edited_subject: Optional[str] = None
    edited_body: Optional[str] = None
    rejection_reason: Optional[str] = None

class ApprovalResponse(BaseModel):
    """Response after processing an approval action."""
    message_id: uuid.UUID
    new_status: str

# ---------------------------------------------------------------------------
# Main Workflow Output
# ---------------------------------------------------------------------------

class PersonalizationResult(BaseModel):
    """Result of the personalization workflow."""
    lead_id: uuid.UUID
    campaign_id: uuid.UUID
    message_id: Optional[uuid.UUID] = None
    status: str
    validation_result: Optional[MessageValidationResult] = None
    errors: list[str] = Field(default_factory=list)
