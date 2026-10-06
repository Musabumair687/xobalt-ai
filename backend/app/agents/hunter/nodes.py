"""LangGraph node functions for the Hunter workflow.

Each function in this module is a LangGraph node.  A node receives the full
HunterState, performs ONE focused step, then returns a dict of the state keys
it wants to update.  It never touches keys it didn't touch.

Node execution order (defined in hunter_workflow.py):

    discover_companies
         ↓
    deduplicate
         ↓
    find_people
         ↓
    enrich
         ↓
    verify
         ↓
    store

Architectural rule
------------------
Nodes **orchestrate**; they do NOT contain provider-specific code.
All API calls go through services → integrations → external providers.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.hunter.state import HunterState
from app.schemas.hunter import DiscoveredCompany, DiscoveredPerson, VerificationResult
from app.services.deduplication_service import DeduplicationService
from app.services.discovery_service import DiscoveryService
from app.services.enrichment_service import EnrichmentService
from app.services.lead_ingestion_service import LeadIngestionService
from app.services.verification_service import VerificationService

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Node: discover_companies
# ---------------------------------------------------------------------------


async def discover_companies(state: HunterState) -> dict[str, Any]:
    """Call DiscoveryService and populate discovered_companies."""
    criteria = state["criteria"]
    logger.info(
        "Hunter › discover_companies | industry=%s country=%s",
        criteria.industry,
        criteria.country,
    )

    service = DiscoveryService()
    try:
        companies = await service.search(criteria)
    except Exception as exc:
        logger.error("Discovery failed: %s", exc)
        return {
            "discovered_companies": [],
            "errors": state.get("errors", []) + [f"discovery_error: {exc}"],
        }

    logger.info("Discovered %d company candidates.", len(companies))
    return {"discovered_companies": companies}


# ---------------------------------------------------------------------------
# Node: deduplicate
# ---------------------------------------------------------------------------


async def deduplicate(state: HunterState) -> dict[str, Any]:
    """Remove duplicate companies using domain normalization."""
    raw = state.get("discovered_companies", [])
    logger.info("Hunter › deduplicate | input=%d companies", len(raw))

    service = DeduplicationService()
    unique = service.deduplicate_companies(raw)

    logger.info("After dedup: %d unique companies.", len(unique))
    return {"deduplicated_companies": unique}


# ---------------------------------------------------------------------------
# Node: find_people
# ---------------------------------------------------------------------------


async def find_people(state: HunterState) -> dict[str, Any]:
    """Find decision makers for each deduplicated company."""
    companies = state.get("deduplicated_companies", [])
    criteria = state["criteria"]
    logger.info("Hunter › find_people | companies=%d", len(companies))

    service = EnrichmentService()
    people_map: dict[str, list[DiscoveredPerson]] = {}
    errors = list(state.get("errors", []))

    for company in companies:
        key = company.domain or company.name
        try:
            people = await service.find_people(company, criteria.decision_maker_roles)
            people_map[key] = people[: criteria.max_people_per_company]
        except Exception as exc:
            logger.warning("find_people failed for %s: %s", key, exc)
            errors.append(f"find_people_error[{key}]: {exc}")
            people_map[key] = []

    return {"people": people_map, "errors": errors}


# ---------------------------------------------------------------------------
# Node: enrich
# ---------------------------------------------------------------------------


async def enrich(state: HunterState) -> dict[str, Any]:
    """Enrich each company with more detailed data from an enrichment provider."""
    companies = state.get("deduplicated_companies", [])
    logger.info("Hunter › enrich | companies=%d", len(companies))

    service = EnrichmentService()
    enriched: list[DiscoveredCompany] = []
    errors = list(state.get("errors", []))

    for company in companies:
        try:
            enriched_company = await service.enrich_company(company)
            enriched.append(enriched_company)
        except Exception as exc:
            key = company.domain or company.name
            logger.warning("Enrichment failed for %s: %s", key, exc)
            errors.append(f"enrich_error[{key}]: {exc}")
            enriched.append(company)  # keep what we have

    return {"enriched_companies": enriched, "errors": errors}


# ---------------------------------------------------------------------------
# Node: verify
# ---------------------------------------------------------------------------


async def verify(state: HunterState) -> dict[str, Any]:
    """Verify every email address collected in the people map."""
    people_map = state.get("people", {})
    logger.info("Hunter › verify | companies=%d", len(people_map))

    service = VerificationService()
    results: list[VerificationResult] = []
    errors = list(state.get("errors", []))

    for company_key, people in people_map.items():
        for person in people:
            if not person.email:
                continue
            try:
                result = await service.verify_email(person.email)
                results.append(result)
            except Exception as exc:
                logger.warning("Verification failed for %s: %s", person.email, exc)
                errors.append(f"verify_error[{person.email}]: {exc}")

    logger.info("Verified %d contacts.", len(results))
    return {"verification_results": results, "errors": errors}


# ---------------------------------------------------------------------------
# Node: store
# ---------------------------------------------------------------------------


async def store(state: HunterState, db: AsyncSession) -> dict[str, Any]:
    """Persist enriched companies, people, contacts, and leads to PostgreSQL.

    This node calls LeadIngestionService which handles all DB writes so that
    individual nodes never manipulate ORM models directly.
    """
    companies = state.get("enriched_companies", state.get("deduplicated_companies", []))
    people_map = state.get("people", {})
    verification_results = state.get("verification_results", [])
    criteria = state["criteria"]

    logger.info("Hunter › store | companies=%d", len(companies))

    service = LeadIngestionService(db)
    lead_ids: list[uuid.UUID] = []
    errors = list(state.get("errors", []))

    for company in companies:
        key = company.domain or company.name
        people = people_map.get(key, [])
        try:
            new_ids = await service.ingest(
                organization_id=criteria.organization_id,
                campaign_id=criteria.campaign_id,
                company=company,
                people=people,
                verification_results=verification_results,
            )
            lead_ids.extend(new_ids)
        except Exception as exc:
            logger.error("Ingestion failed for %s: %s", key, exc)
            errors.append(f"store_error[{key}]: {exc}")

    logger.info("Stored %d leads.", len(lead_ids))
    return {"lead_ids": lead_ids, "errors": errors}
