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
from app.schemas.hunter import (
    DiscoveredCompany,
    DiscoveredPerson,
    VerificationResult,
    VerificationStatus,
)
from app.services.deduplication_service import DeduplicationService
from app.services.discovery_service import DiscoveryService
from app.services.enrichment_service import EnrichmentService
from app.services.lead_ingestion_service import LeadIngestionService
from app.services.verification_service import VerificationService
from app.integrations.provider_errors import safe_provider_error

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

    steps = dict(state.get("steps", {}))
    service = None
    try:
        service = DiscoveryService()
        companies = await service.search(criteria)
    except Exception as exc:
        logger.error("Discovery failed (%s).", type(exc).__name__)
        safe_error = safe_provider_error(
            service.provider_name
            if service is not None
            else "discovery",
            exc,
        )
        error = f"Discovery failed: {safe_error}"
        steps["discovery"] = {
            "status": "failed",
            "error_type": safe_error.error_type,
            "message": str(safe_error),
            "provider_results": (
                service.last_provider_status if service is not None else []
            ),
        }
        return {
            "discovered_companies": [],
            "errors": state.get("errors", []) + [error],
            "steps": steps,
        }

    logger.info("Discovered %d company candidates.", len(companies))
    steps["discovery"] = {
        "status": "succeeded",
        "provider": service.provider_name,
        "mode": service.mode,
        "result_count": len(companies),
        "provider_results": service.last_provider_status,
    }
    return {"discovered_companies": companies, "steps": steps}


# ---------------------------------------------------------------------------
# Node: deduplicate
# ---------------------------------------------------------------------------


async def deduplicate(state: HunterState) -> dict[str, Any]:
    """Remove duplicate companies using domain normalization."""
    steps = dict(state.get("steps", {}))
    if steps.get("discovery", {}).get("status") == "failed":
        steps["deduplication"] = {"status": "skipped", "reason": "discovery_failed"}
        return {"deduplicated_companies": [], "steps": steps}

    raw = state.get("discovered_companies", [])
    logger.info("Hunter › deduplicate | input=%d companies", len(raw))

    service = DeduplicationService()
    unique = service.deduplicate_companies(raw)

    logger.info("After dedup: %d unique companies.", len(unique))
    steps["deduplication"] = {
        "status": "succeeded",
        "input_count": len(raw),
        "result_count": len(unique),
    }
    return {"deduplicated_companies": unique, "steps": steps}


# ---------------------------------------------------------------------------
# Node: find_people
# ---------------------------------------------------------------------------


async def find_people(state: HunterState) -> dict[str, Any]:
    """Find decision makers for each deduplicated company."""
    companies = state.get("deduplicated_companies", [])
    criteria = state["criteria"]
    logger.info("Hunter › find_people | companies=%d", len(companies))

    steps = dict(state.get("steps", {}))
    if not companies:
        steps["people_discovery"] = {
            "status": "skipped",
            "reason": "no_companies_to_enrich",
        }
        return {"people": {}, "steps": steps}

    people_map: dict[str, list[DiscoveredPerson]] = {}
    errors = list(state.get("errors", []))
    failed = 0
    skipped = 0

    try:
        service = EnrichmentService()
        for company in companies:
            key = company.domain or company.name
            try:
                people = await service.find_people(company, criteria.decision_maker_roles)
                people_map[key] = people[: criteria.max_people_per_company]
                if service.last_operation_skipped:
                    skipped += 1
            except Exception as exc:
                failed += 1
                logger.warning("find_people failed for %s (%s).", key, type(exc).__name__)
                provider_error = safe_provider_error(service.provider_name, exc)
                errors.append(f"People discovery failed for {key}: {provider_error}")
                people_map[key] = []
        provider_name = service.provider_name
        mode = service.mode
    except Exception as exc:
        failed += len(companies)
        provider_name = "enrichment"
        mode = "real"
        provider_error = safe_provider_error(provider_name, exc)
        errors.append(f"People discovery failed: {provider_error}")
        people_map = {company.domain or company.name: [] for company in companies}

    steps["people_discovery"] = {
        "status": "failed" if failed else (
            "skipped" if skipped == len(companies) else "succeeded"
        ),
        "skipped_company_count": skipped,
        "provider": provider_name,
        "mode": mode,
        "company_count": len(companies),
        "people_count": sum(len(people) for people in people_map.values()),
        "failed_company_count": failed,
    }
    return {"people": people_map, "errors": errors, "steps": steps}


# ---------------------------------------------------------------------------
# Node: enrich
# ---------------------------------------------------------------------------


async def enrich(state: HunterState) -> dict[str, Any]:
    """Enrich each company with more detailed data from an enrichment provider."""
    companies = state.get("deduplicated_companies", [])
    logger.info("Hunter › enrich | companies=%d", len(companies))

    steps = dict(state.get("steps", {}))
    if not companies:
        steps["enrichment"] = {"status": "skipped", "reason": "no_companies_to_enrich"}
        return {"enriched_companies": [], "steps": steps}

    enriched: list[DiscoveredCompany] = []
    errors = list(state.get("errors", []))
    failed = 0
    skipped = 0

    try:
        service = EnrichmentService()
        for company in companies:
            try:
                enriched.append(await service.enrich_company(company))
                if service.last_operation_skipped:
                    skipped += 1
            except Exception as exc:
                failed += 1
                key = company.domain or company.name
                logger.warning("Enrichment failed for %s (%s).", key, type(exc).__name__)
                errors.append(f"Enrichment failed for {key}: {safe_provider_error(service.provider_name, exc)}")
                enriched.append(company)
        provider_name = service.provider_name
        mode = service.mode
    except Exception as exc:
        failed += len(companies)
        provider_name = "enrichment"
        mode = "real"
        errors.append(f"Enrichment failed: {safe_provider_error(provider_name, exc)}")
        enriched = list(companies)

    steps["enrichment"] = {
        "status": "failed" if failed else (
            "skipped" if skipped == len(companies) else "succeeded"
        ),
        "provider": provider_name,
        "mode": mode,
        "company_count": len(companies),
        "skipped_company_count": skipped,
        "failed_company_count": failed,
    }
    return {"enriched_companies": enriched, "errors": errors, "steps": steps}


# ---------------------------------------------------------------------------
# Node: verify
# ---------------------------------------------------------------------------


async def verify(state: HunterState) -> dict[str, Any]:
    """Verify every email address collected in the people map."""
    people_map = state.get("people", {})
    logger.info("Hunter › verify | companies=%d", len(people_map))

    steps = dict(state.get("steps", {}))
    email_count = sum(bool(person.email) for people in people_map.values() for person in people)
    if not email_count:
        steps["verification"] = {
            "status": "skipped",
            "reason": "no_email_addresses",
            "result_count": 0,
        }
        return {"verification_results": [], "steps": steps}

    results: list[VerificationResult] = []
    errors = list(state.get("errors", []))
    failed = 0
    skipped = 0

    try:
        service = VerificationService()
        for company_key, people in people_map.items():
            for person in people:
                if not person.email:
                    continue
                try:
                    result = await service.verify_email(person.email)
                    results.append(result)
                    if result.status == VerificationStatus.skipped:
                        skipped += 1
                    if result.reason == "api_error":
                        failed += 1
                        errors.append(
                            f"Email verification failed for {company_key} "
                            f"({result.provider or 'provider'})."
                        )
                except Exception as exc:
                    failed += 1
                    logger.warning("Verification failed (%s).", type(exc).__name__)
                    errors.append(
                        f"Email verification failed for {company_key}: "
                        f"{safe_provider_error(service.provider_name, exc)}"
                    )
        provider_name = service.provider_name
        mode = service.mode
    except Exception as exc:
        failed += 1
        provider_name = "verification"
        mode = "real"
        errors.append(f"Email verification failed: {safe_provider_error(provider_name, exc)}")

    logger.info("Verified %d contacts.", len(results))
    steps["verification"] = {
        "status": "failed" if failed else (
            "skipped" if skipped == len(results) and results else "succeeded"
        ),
        "provider": provider_name,
        "mode": mode,
        "email_count": email_count,
        "result_count": len(results),
        "skipped_count": skipped,
        "failed_count": failed,
    }
    return {"verification_results": results, "errors": errors, "steps": steps}


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
    steps = dict(state.get("steps", {}))

    if steps.get("discovery", {}).get("status") == "failed":
        steps["persistence"] = {"status": "skipped", "reason": "discovery_failed"}
        return {"lead_ids": [], "steps": steps}

    logger.info("Hunter › store | companies=%d", len(companies))

    service = LeadIngestionService(db)
    lead_ids: list[uuid.UUID] = []
    errors = list(state.get("errors", []))
    failed = 0

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
            failed += 1
            safe_error = safe_provider_error("persistence", exc)
            logger.error("Ingestion failed for %s (%s).", key, safe_error.error_type)
            await db.rollback()
            errors.append(f"store_error[{key}]: {safe_error}")

    logger.info("Stored %d leads.", len(lead_ids))
    steps["persistence"] = {
        "status": "failed" if failed else "succeeded",
        "lead_count": len(lead_ids),
        "company_count": len(companies),
        "failed_company_count": failed,
    }
    return {"lead_ids": lead_ids, "errors": errors, "steps": steps}
