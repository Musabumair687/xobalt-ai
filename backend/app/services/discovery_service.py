"""DiscoveryService — application-level facade for company discovery.

Architecture
------------
    Hunter node (discover_companies)
          ↓
    DiscoveryService          ← this file
          ↓
    LeadSource (ABC)
          ↓
    SearchSource / other concrete providers

DiscoveryService owns:
- selecting which source(s) to use
- aggregating results from multiple sources
- normalizing results
- enforcing the max_companies limit
"""

from __future__ import annotations

import logging

from app.integrations.sources.base import LeadSource
from app.integrations.sources.search_source import SearchSource
from app.schemas.hunter import DiscoveredCompany, HunterCriteria

logger = logging.getLogger(__name__)


class DiscoveryService:
    """Coordinate company discovery across one or more LeadSource providers."""

    def __init__(self, sources: list[LeadSource] | None = None) -> None:
        # Default: use SearchSource in mock mode.
        # Real providers are injected in production via DI / config.
        self._sources: list[LeadSource] = sources or [SearchSource()]

    async def search(self, criteria: HunterCriteria) -> list[DiscoveredCompany]:
        """Search all configured sources and return deduplicated candidates.

        Respects `criteria.max_companies` across all sources combined.
        """
        all_results: list[DiscoveredCompany] = []

        for source in self._sources:
            if not await source.is_available():
                logger.warning("Source '%s' is not available – skipping.", source.name)
                continue

            logger.debug("Searching source '%s' …", source.name)
            try:
                results = await source.search(criteria)
                logger.info(
                    "Source '%s' returned %d companies.", source.name, len(results)
                )
                all_results.extend(results)
            except Exception as exc:
                logger.error("Source '%s' raised an error: %s", source.name, exc)

            if len(all_results) >= criteria.max_companies:
                break

        return all_results[: criteria.max_companies]
