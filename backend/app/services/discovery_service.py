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
from app.integrations.provider_errors import (
    ProviderConfigurationError,
    safe_provider_error,
)
from app.schemas.hunter import DiscoveredCompany, HunterCriteria

logger = logging.getLogger(__name__)


class DiscoveryService:
    """Coordinate company discovery across one or more LeadSource providers."""

    def __init__(self, sources: list[LeadSource] | None = None) -> None:
        if sources is not None:
            self._sources = sources
        else:
            from app.services.integration_settings_service import get_runtime_settings
            settings = get_runtime_settings()
            provider = settings.DISCOVERY_PROVIDER.lower().strip()
            if provider == "auto":
                if settings.SERPAPI_API_KEY:
                    provider = "serpapi"
                elif settings.TAVILY_API_KEY:
                    provider = "tavily"
                else:
                    raise ProviderConfigurationError(
                        "Discovery provider is auto but no real provider is configured; "
                        "select DISCOVERY_PROVIDER=mock for mock mode."
                    )

            if provider == "mock":
                self._sources = [SearchSource(provider="mock")]
            elif provider in ("ddg", "duckduckgo"):
                from app.integrations.sources.duckduckgo_source import DuckDuckGoSource
                self._sources = [DuckDuckGoSource()]
            elif provider == "serpapi":
                if not settings.SERPAPI_API_KEY:
                    raise ProviderConfigurationError("SerpAPI is selected but has no API key.")
                self._sources = [
                    SearchSource(api_key=settings.SERPAPI_API_KEY, provider="serpapi")
                ]
            elif provider == "tavily":
                if not settings.TAVILY_API_KEY:
                    raise ProviderConfigurationError("Tavily is selected but has no API key.")
                self._sources = [
                    SearchSource(api_key=settings.TAVILY_API_KEY, provider="tavily")
                ]
            else:
                raise ProviderConfigurationError(
                    f"Unsupported discovery provider: {provider or 'empty'}."
                )
        self.last_provider_status: list[dict[str, object]] = []

    @property
    def provider_name(self) -> str:
        return ", ".join(source.name for source in self._sources)

    @property
    def mode(self) -> str:
        return "mock" if self._sources and all("mock" in source.name for source in self._sources) else "real"

    async def search(self, criteria: HunterCriteria) -> list[DiscoveredCompany]:
        """Search all configured sources and return deduplicated candidates.

        Respects `criteria.max_companies` across all sources combined.
        """
        all_results: list[DiscoveredCompany] = []
        self.last_provider_status = []

        for source in self._sources:
            if not await source.is_available():
                self.last_provider_status.append(
                    {"provider": source.name, "status": "failed", "error": "provider_unavailable"}
                )
                raise ProviderConfigurationError(
                    f"Discovery provider {source.name} is unavailable."
                )

            logger.debug("Searching source '%s' …", source.name)
            try:
                results = await source.search(criteria)
                self.last_provider_status.append(
                    {
                        "provider": source.name,
                        "status": "succeeded",
                        "result_count": len(results),
                    }
                )
                all_results.extend(results)
            except Exception as exc:
                self.last_provider_status.append(
                    {
                        "provider": source.name,
                        "status": "failed",
                        "error": type(safe_provider_error(source.name, exc)).__name__,
                        "error_type": type(exc).__name__,
                    }
                )
                raise safe_provider_error(source.name, exc) from exc

            if len(all_results) >= criteria.max_companies:
                break

        return all_results[: criteria.max_companies]
