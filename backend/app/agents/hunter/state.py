"""Hunter agent state definition for the LangGraph workflow.

The HunterState TypedDict travels through every LangGraph node.
Each node reads from it and adds/updates its section.

Node responsibility map
-----------------------
discover_companies  → populates `discovered_companies`
deduplicate         → populates `deduplicated_companies`
find_people         → populates `people`
enrich              → enriches entries in `companies` and `people`
verify              → populates `verification_results`
store               → populates `lead_ids`

`errors` and `warnings` can be written by any node.
"""

from __future__ import annotations

import uuid
from typing import Annotated, Any, Optional

from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from app.schemas.hunter import (
    DiscoveredCompany,
    DiscoveredPerson,
    HunterCriteria,
    VerificationResult,
)


class HunterState(TypedDict):
    """Mutable state object that flows through the Hunter LangGraph workflow."""

    # ---- Input ----
    criteria: HunterCriteria
    """ICP criteria provided by the campaign that triggered this Hunter run."""

    # ---- Discovery stage ----
    discovered_companies: list[DiscoveredCompany]
    """Raw company candidates from the discovery source (may contain duplicates)."""

    # ---- Deduplication stage ----
    deduplicated_companies: list[DiscoveredCompany]
    """Unique companies after domain-based deduplication."""

    # ---- People stage ----
    # Keyed by (company_name OR domain) → list of people found.
    people: dict[str, list[DiscoveredPerson]]
    """Decision-makers found for each company."""

    # ---- Enrichment stage ----
    enriched_companies: list[DiscoveredCompany]
    """Companies after enrichment (more fields filled in)."""

    # ---- Verification stage ----
    verification_results: list[VerificationResult]
    """Verification outcome for every email/contact collected."""

    # ---- Storage stage ----
    lead_ids: list[uuid.UUID]
    """UUIDs of Lead rows created in PostgreSQL during the store stage."""

    # ---- Run health ----
    errors: list[str]
    """Non-fatal errors accumulated during the run (per-company failures, etc.)."""

    warnings: list[str]
    """Advisory messages that don't stop the workflow."""
