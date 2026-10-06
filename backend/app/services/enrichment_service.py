"""EnrichmentService — coordinate company enrichment and people discovery.

Architecture
------------
    Hunter node (enrich / find_people)
          ↓
    EnrichmentService           ← this file
          ↓
    EnrichmentProvider (ABC)
          ↓
    Real provider (Apollo, Clearbit, …) — injected in Phase 4+

Phase 3 ships with a MockEnrichmentProvider so the workflow runs
end-to-end without live API credentials.  The real provider is plugged
in later by implementing EnrichmentProvider and injecting it here.
"""

from __future__ import annotations

import logging

from app.integrations.enrichment.base import EnrichmentProvider
from app.schemas.hunter import DiscoveredCompany, DiscoveredPerson

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Mock provider — used in Phase 3 / tests
# ---------------------------------------------------------------------------


class MockEnrichmentProvider(EnrichmentProvider):
    """No-op enrichment provider used during development and testing."""

    @property
    def name(self) -> str:
        return "mock_enrichment"

    async def is_available(self) -> bool:
        return True

    async def enrich_company(self, company: DiscoveredCompany) -> DiscoveredCompany:
        """Return the company unchanged (mock — no real API call)."""
        logger.debug("MockEnrichmentProvider: enrich_company('%s') — no-op.", company.name)
        return company

    async def find_people(
        self, company: DiscoveredCompany, roles: list[str]
    ) -> list[DiscoveredPerson]:
        """Return an empty list (mock — no real API call)."""
        logger.debug(
            "MockEnrichmentProvider: find_people('%s', %s) — no-op.",
            company.name,
            roles,
        )
        return []


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class EnrichmentService:
    """Application-level facade for company enrichment and people discovery."""

    def __init__(self, provider: EnrichmentProvider | None = None) -> None:
        # Default to mock provider; real provider injected via DI / config.
        self._provider: EnrichmentProvider = provider or MockEnrichmentProvider()

    async def enrich_company(self, company: DiscoveredCompany) -> DiscoveredCompany:
        """Enrich a company with data from the configured provider.

        Falls back to returning the original company if enrichment fails.
        """
        if not await self._provider.is_available():
            logger.warning(
                "EnrichmentProvider '%s' is unavailable – skipping enrichment.",
                self._provider.name,
            )
            return company

        logger.debug("Enriching company '%s' via '%s'.", company.name, self._provider.name)
        return await self._provider.enrich_company(company)

    async def find_people(
        self, company: DiscoveredCompany, roles: list[str]
    ) -> list[DiscoveredPerson]:
        """Find decision makers for *company* matching *roles*.

        Returns an empty list if the provider is unavailable.
        """
        if not await self._provider.is_available():
            logger.warning(
                "EnrichmentProvider '%s' is unavailable – skipping people discovery.",
                self._provider.name,
            )
            return []

        logger.debug(
            "Finding people at '%s' for roles %s via '%s'.",
            company.name,
            roles,
            self._provider.name,
        )
        return await self._provider.find_people(company, roles)
