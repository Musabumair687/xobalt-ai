"""SerpAPI (Google Search) provider for lead discovery."""

from __future__ import annotations

import logging
from urllib.parse import urlparse
import httpx

from app.integrations.sources.base import LeadSource
from app.integrations.provider_errors import ProviderConfigurationError, safe_provider_error
from app.schemas.hunter import DiscoveredCompany, HunterCriteria

logger = logging.getLogger(__name__)


class SerpApiSource(LeadSource):
    """Company discovery via SerpAPI Google Search.
    
    Returns genuine organic Google search results for target ICP.
    Free tier offers 100 searches/month.
    """

    def __init__(self, api_key: str = "") -> None:
        self._api_key = api_key

    @property
    def name(self) -> str:
        return "serpapi"

    async def is_available(self) -> bool:
        return bool(self._api_key)

    async def search(self, criteria: HunterCriteria) -> list[DiscoveredCompany]:
        if not self._api_key:
            raise ProviderConfigurationError("SerpAPI is selected but has no API key.")

        query = f"top {criteria.industry} companies in {criteria.country}"
        logger.info("SerpApiSource searching: '%s'", query)

        params = {
            "engine": "google",
            "q": query,
            "api_key": self._api_key,
            "num": min(criteria.max_companies * 2, 30),
        }

        try:
            async with httpx.AsyncClient(timeout=25.0) as client:
                response = await client.get("https://serpapi.com/search.json", params=params)
                response.raise_for_status()
                data = response.json()
        except Exception as exc:
            logger.error("SerpAPI request failed (%s).", type(exc).__name__)
            raise safe_provider_error(self.name, exc) from exc

        companies: list[DiscoveredCompany] = []
        seen_domains = set()

        for res in data.get("organic_results", []):
            link = res.get("link", "")
            title = res.get("title", "")
            snippet = res.get("snippet", "")

            try:
                parsed = urlparse(link)
                domain = parsed.netloc.lower()
                if domain.startswith("www."):
                    domain = domain[4:]
            except Exception:
                continue

            if not domain or domain in seen_domains:
                continue

            # Skip aggregators and directories
            if any(agg in domain for agg in ["linkedin.com", "facebook.com", "instagram.com", "wikipedia.org", "yelp.com", "yellowpages.com"]):
                continue

            seen_domains.add(domain)

            name = title.split(" - ")[0].split(" | ")[0].strip() or domain

            companies.append(
                DiscoveredCompany(
                    name=name,
                    domain=domain,
                    website_url=f"https://{domain}",
                    country=criteria.country,
                    industry=criteria.industry,
                    source="serpapi",
                    raw_data={"snippet": snippet[:200], "source_url": link},
                )
            )

            if len(companies) >= criteria.max_companies:
                break

        return companies
