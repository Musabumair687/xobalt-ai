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
        self._provider = provider.lower()
        self._delegate: LeadSource | None = None

        if self._provider in ("serp", "serpapi"):
            from app.integrations.sources.serpapi_source import SerpApiSource
            self._delegate = SerpApiSource(api_key=api_key)
        elif self._provider == "tavily":
            from app.integrations.sources.tavily_source import TavilySource
            self._delegate = TavilySource(api_key=api_key)
        elif self._provider in ("duckduckgo", "ddg"):
            from app.integrations.sources.duckduckgo_source import DuckDuckGoSource
            self._delegate = DuckDuckGoSource()

    @property
    def name(self) -> str:
        return f"search_source:{self._provider}"

    async def is_available(self) -> bool:
        if self._delegate:
            return await self._delegate.is_available()
        if self._provider == "mock":
            return True
        return bool(self._api_key)

    async def search(self, criteria: HunterCriteria) -> list[DiscoveredCompany]:
        """Discover companies matching *criteria*."""
        if self._delegate:
            return await self._delegate.search(criteria)

        if self._provider == "mock":
            logger.debug("SearchSource running in mock mode – returning empty results.")
            return []

        logger.warning(
            "SearchSource: provider '%s' not supported. Returning empty list.",
            self._provider,
        )
        return []
