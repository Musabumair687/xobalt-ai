"""Base interface for all company/person enrichment providers.

Enrichment answers: 'Give me more detail about this company / person.'
Any provider (Apollo, Clearbit, Hunter.io, etc.) must implement EnrichmentProvider.
"""
from abc import ABC, abstractmethod

from app.schemas.hunter import DiscoveredCompany, DiscoveredPerson


class EnrichmentProvider(ABC):
    """Abstract base class for enrichment providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable provider identifier."""
        ...

    @abstractmethod
    async def enrich_company(self, company: DiscoveredCompany) -> DiscoveredCompany:
        """Enrich a company with additional data (employees, description, etc.).

        Args:
            company: Partially-filled company data from discovery.

        Returns:
            The same company with any additional fields filled in.
        """
        ...

    @abstractmethod
    async def find_people(
        self, company: DiscoveredCompany, roles: list[str]
    ) -> list[DiscoveredPerson]:
        """Find decision-maker contacts for a company.

        Args:
            company: Enriched company data.
            roles:   List of job-title keywords to match (e.g. ['CEO', 'Founder']).

        Returns:
            List of discovered people with whatever contact info is available.
        """
        ...

    @abstractmethod
    async def is_available(self) -> bool:
        """Return True if the provider is configured and reachable."""
        ...
