"""Base interface for all lead discovery sources.

Any provider that can search for companies must implement LeadSource.
This keeps the workflow independent of any specific vendor.
"""
from abc import ABC, abstractmethod
from typing import Any

from app.schemas.hunter import HunterCriteria, DiscoveredCompany


class LeadSource(ABC):
    """Abstract base class for all company discovery sources."""

    @abstractmethod
    async def search(self, criteria: HunterCriteria) -> list[DiscoveredCompany]:
        """Search for companies matching the given ICP criteria.

        Args:
            criteria: Structured hunter criteria (industry, country, employees, roles).

        Returns:
            A list of discovered company candidates normalized into DiscoveredCompany.
        """
        ...

    @abstractmethod
    async def is_available(self) -> bool:
        """Check whether this source is currently reachable/configured."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable identifier for this source (e.g. 'google_cse', 'apollo')."""
        ...
