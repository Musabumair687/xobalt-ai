"""Search-based company discovery source (provider-agnostic skeleton).

This file implements a concrete LeadSource that calls an external search
API. The exact provider (Google CSE, SerpAPI, Exa, etc.) is injected via
configuration so we never lock the architecture to one vendor.

During Phase 3 the class is functional but calls a mock by default so
tests can run without live API credentials. A real provider adapter will
be plugged in once we evaluate coverage and cost in Phase 4.
"""
from __future__ import annotations

import logging
from typing import Any

from app.integrations.sources.base import LeadSource
from app.schemas.hunter import DiscoveredCompany, HunterCriteria

logger = logging.getLogger(__name__)


class SearchSource(LeadSource):
    """Company discovery via a configurable web-search backend.

    Usage::

        source = SearchSource(api_key="...", provider="serp")
        companies = await source.search(criteria)
    """

    def __init__(self, api_key: str = "", provider: str = "mock") -> None:
        self._api_key = api_key
        self._provider = provider

    @property
    def name(self) -> str:
        return f"search_source:{self._provider}"

    async def is_available(self) -> bool:
        if self._provider == "mock":
            return True
        return bool(self._api_key)

    async def search(self, criteria: HunterCriteria) -> list[DiscoveredCompany]:
        """Discover companies matching *criteria*.

        In mock mode returns an empty list so the workflow can be exercised
        end-to-end in tests without network calls.
        """
        if self._provider == "mock":
            logger.debug("SearchSource running in mock mode – returning empty results.")
            return []

        # TODO: plug in real provider adapter (Phase 4 Website Intelligence)
        logger.warning(
            "SearchSource: provider '%s' not yet implemented. Returning empty list.",
            self._provider,
        )
        return []
