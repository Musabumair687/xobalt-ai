"""Pydantic schemas for the Hunter workflow.

These models define the data contracts that travel through the Hunter
LangGraph workflow.  They are separate from the SQLAlchemy ORM models
because the workflow works with in-flight, not-yet-persisted data.

Structure
---------
HunterCriteria       – Input from a campaign (ICP filters).
DiscoveredCompany    – Candidate company returned by a discovery source.
DiscoveredPerson     – Candidate decision-maker returned by enrichment.
VerificationResult   – Result of verifying a single contact.
HunterResult         – Final summary produced after a full Hunter run.
"""

from __future__ import annotations

import uuid
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, HttpUrl, field_validator


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class VerificationStatus(str, Enum):
    valid = "valid"
    invalid = "invalid"
    risky = "risky"
    unknown = "unknown"
    skipped = "skipped"


class HunterRunStatus(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------


class HunterCriteria(BaseModel):
    """Structured ICP (Ideal Customer Profile) criteria for a Hunter run.

    A campaign passes this object to the Hunter workflow to control which
    companies and people will be discovered.
    """

    organization_id: uuid.UUID = Field(
        ..., description="Owning organization – used when persisting leads."
    )
    campaign_id: Optional[uuid.UUID] = Field(
        default=None,
        description="If set, discovered leads are linked to this campaign.",
    )

    # --- company filters ---
    industry: str = Field(..., examples=["Real Estate"])
    country: str = Field(default="US", examples=["US"])
    min_employees: Optional[int] = Field(default=None, ge=1)
    max_employees: Optional[int] = Field(default=None, ge=1)
    keywords: list[str] = Field(
        default_factory=list,
        description="Extra search keywords (city, niche, etc.).",
    )

    # --- people filters ---
    decision_maker_roles: list[str] = Field(
        default_factory=lambda: ["CEO", "Founder", "Owner"],
        description="Job-title keywords used to identify decision makers.",
    )

    # --- run limits ---
    max_companies: int = Field(
        default=50,
        ge=1,
        le=500,
        description="Maximum companies to discover in one run.",
    )
    max_people_per_company: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum decision makers to enrich per company.",
    )

    @field_validator("max_employees")
    @classmethod
    def max_must_exceed_min(cls, v: Optional[int], info: Any) -> Optional[int]:
        min_val = info.data.get("min_employees")
        if v is not None and min_val is not None and v < min_val:
            raise ValueError("max_employees must be >= min_employees")
        return v


# ---------------------------------------------------------------------------
# Discovery output
# ---------------------------------------------------------------------------


class DiscoveredCompany(BaseModel):
    """A company candidate returned from a discovery or enrichment source.

    Fields are all optional (except name) because providers differ in what
    they return – the enrichment step fills in the blanks.
    """

    name: str
    domain: Optional[str] = None
    website_url: Optional[str] = None
    industry: Optional[str] = None
    employee_count: Optional[int] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    description: Optional[str] = None
    linkedin_url: Optional[str] = None
    source: Optional[str] = Field(
        default=None,
        description="Which provider/source returned this company.",
    )
    raw_data: Optional[dict[str, Any]] = Field(
        default=None,
        description="Original provider payload kept for audit/debugging.",
    )


class DiscoveredPerson(BaseModel):
    """A decision-maker candidate linked to a DiscoveredCompany."""

    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    job_title: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None
    source: Optional[str] = None
    raw_data: Optional[dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------


class VerificationResult(BaseModel):
    """Result of verifying a single contact value (usually email)."""

    contact_value: str = Field(..., description="The email / phone being verified.")
    status: VerificationStatus = VerificationStatus.unknown
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Provider confidence score (0 = no confidence, 1 = certain).",
    )
    provider: Optional[str] = Field(
        default=None, description="Name of the verification provider used."
    )
    reason: Optional[str] = Field(
        default=None, description="Human-readable explanation from the provider."
    )
    raw_data: Optional[dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Run-level output
# ---------------------------------------------------------------------------


class HunterResult(BaseModel):
    """Summary produced at the end of a complete Hunter workflow run."""

    run_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    status: HunterRunStatus = HunterRunStatus.completed
    criteria: HunterCriteria

    companies_discovered: int = 0
    companies_after_dedup: int = 0
    people_found: int = 0
    contacts_verified: int = 0
    leads_created: int = 0

    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
