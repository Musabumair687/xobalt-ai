"""Pydantic schemas for Website Intelligence (Phase 4).

These schemas define the data contracts for website crawling,
content extraction, and structured intelligence output.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class PageType(str, Enum):
    home = "home"
    about = "about"
    services = "services"
    contact = "contact"
    projects = "projects"
    team = "team"
    other = "other"


class CrawlStatus(str, Enum):
    pending = "pending"
    crawling = "crawling"
    completed = "completed"
    failed = "failed"


# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------


class WebsiteIntelligenceRequest(BaseModel):
    """Request to trigger website intelligence for a company."""

    company_id: uuid.UUID = Field(
        ..., description="The company whose website to analyze."
    )
    force_recrawl: bool = Field(
        default=False,
        description="If True, recrawl even if intelligence already exists.",
    )


# ---------------------------------------------------------------------------
# Page discovery & content
# ---------------------------------------------------------------------------


class DiscoveredPage(BaseModel):
    """A page discovered on a company website."""

    url: str
    page_type: PageType = PageType.other
    title: Optional[str] = None


class FetchedPage(BaseModel):
    """A page that has been fetched and its content cleaned."""

    url: str
    page_type: PageType = PageType.other
    title: Optional[str] = None
    status_code: int = 200
    raw_html: Optional[str] = Field(default=None, exclude=True)
    clean_text: str = ""
    content_length: int = 0


# ---------------------------------------------------------------------------
# Structured intelligence output (what the LLM returns)
# ---------------------------------------------------------------------------


class ExtractedIntelligence(BaseModel):
    """Structured business intelligence extracted from website content.

    The LLM must only populate fields supported by the actual page content.
    No hallucination allowed.
    """

    services: list[str] = Field(
        default_factory=list,
        description="Products or services the company offers.",
    )
    target_market: list[str] = Field(
        default_factory=list,
        description="Who the company serves (e.g. 'Home buyers', 'Commercial investors').",
    )
    locations: list[str] = Field(
        default_factory=list,
        description="Cities, states, or regions where the company operates.",
    )
    unique_selling_points: list[str] = Field(
        default_factory=list,
        description="What differentiates the company (awards, guarantees, specialties).",
    )
    projects: list[str] = Field(
        default_factory=list,
        description="Notable projects, case studies, or portfolio items.",
    )
    contact_info: list[str] = Field(
        default_factory=list,
        description="Phone numbers, emails, or office addresses found on site.",
    )
    technology: list[str] = Field(
        default_factory=list,
        description="Tech stack or tools mentioned (CRM, platforms, integrations).",
    )


class IntelligenceWithEvidence(BaseModel):
    """Intelligence plus source evidence so every claim is traceable."""

    intelligence: ExtractedIntelligence
    evidence: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Maps each intelligence field to source text snippets.",
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="LLM self-reported confidence (0 = low, 1 = high).",
    )
    pages_analyzed: int = 0
    model_used: Optional[str] = None


# ---------------------------------------------------------------------------
# API response
# ---------------------------------------------------------------------------


class WebsiteIntelligenceResponse(BaseModel):
    """API response after triggering or retrieving website intelligence."""

    company_id: uuid.UUID
    website_url: Optional[str] = None
    status: CrawlStatus = CrawlStatus.completed
    intelligence: Optional[ExtractedIntelligence] = None
    evidence: Optional[dict[str, list[str]]] = None
    pages_analyzed: int = 0
    confidence: float = 0.0
    extracted_at: Optional[datetime] = None
    errors: list[str] = Field(default_factory=list)
