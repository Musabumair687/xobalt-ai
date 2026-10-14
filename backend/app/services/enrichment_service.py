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
from app.integrations.provider_errors import ProviderConfigurationError
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
        self.mode = "injected" if provider is not None else "configured"
        self.last_operation_skipped = False
        if provider is not None:
            self._provider = provider
            return

        from app.services.integration_settings_service import get_runtime_settings
        settings = get_runtime_settings()

        selected = settings.ENRICHMENT_PROVIDER.lower().strip()
        if selected == "mock":
            self._provider = MockEnrichmentProvider()
        elif selected == "apollo":
            if not settings.APOLLO_API_KEY:
                raise ProviderConfigurationError("Apollo is selected but has no API key.")
            from app.integrations.enrichment.apollo import ApolloEnrichmentProvider
            self._provider = ApolloEnrichmentProvider(api_key=settings.APOLLO_API_KEY)
        elif selected == "hunter":
            if not settings.HUNTER_API_KEY:
                raise ProviderConfigurationError("Hunter is selected but has no API key.")
            from app.integrations.enrichment.hunter_enrichment import HunterEnrichmentProvider
            self._provider = HunterEnrichmentProvider(api_key=settings.HUNTER_API_KEY)
        elif selected == "auto":
            if settings.APOLLO_API_KEY:
                from app.integrations.enrichment.apollo import ApolloEnrichmentProvider
                self._provider = ApolloEnrichmentProvider(api_key=settings.APOLLO_API_KEY)
            elif settings.HUNTER_API_KEY:
                from app.integrations.enrichment.hunter_enrichment import HunterEnrichmentProvider
                self._provider = HunterEnrichmentProvider(api_key=settings.HUNTER_API_KEY)
            else:
                raise ProviderConfigurationError(
                    "Enrichment provider is auto but no real provider is configured; "
                    "select ENRICHMENT_PROVIDER=mock for mock mode."
                )
        else:
            raise ProviderConfigurationError(
                f"Unsupported enrichment provider: {selected or 'empty'}."
            )
        self.mode = "mock" if isinstance(self._provider, MockEnrichmentProvider) else "real"

    @property
    def provider_name(self) -> str:
        return self._provider.name

    async def enrich_company(self, company: DiscoveredCompany) -> DiscoveredCompany:
        """Enrich a company with data from the configured provider.

        Returns the provider result; failures are raised for the workflow to record.
        """
        if not await self._provider.is_available():
            self.last_operation_skipped = True
            logger.warning("Enrichment provider '%s' is unavailable; skipping.", self._provider.name)
            return company

        self.last_operation_skipped = False
        logger.debug("Enriching company '%s' via '%s'.", company.name, self._provider.name)
        return await self._provider.enrich_company(company)

    async def find_people(
        self, company: DiscoveredCompany, roles: list[str]
    ) -> list[DiscoveredPerson]:
        """Find decision makers for *company* matching *roles*.

        Provider errors are raised rather than represented as an empty result.
        """
        if not await self._provider.is_available():
            self.last_operation_skipped = True
            logger.warning("Enrichment provider '%s' is unavailable; skipping.", self._provider.name)
            return []

        self.last_operation_skipped = False
        logger.debug(
            "Finding people at '%s' for roles %s via '%s'.",
            company.name,
            roles,
            self._provider.name,
        )
        return await self._provider.find_people(company, roles)
