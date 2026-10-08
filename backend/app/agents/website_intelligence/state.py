"""State definition for the Website Intelligence workflow."""

import uuid
from typing import TypedDict, Any
from app.schemas.website_intelligence import DiscoveredPage, FetchedPage, IntelligenceWithEvidence

class WebsiteIntelligenceState(TypedDict, total=False):
    """The state dictionary travelling through the Website Intelligence LangGraph."""
    company_id: uuid.UUID
    website_url: str
    
    # Workflow progression
    discovered_pages: list[DiscoveredPage]
    fetched_pages: list[FetchedPage]
    
    # Result
    extracted_intelligence: IntelligenceWithEvidence | None
    
    # Telemetry
    errors: list[str]
    warnings: list[str]
