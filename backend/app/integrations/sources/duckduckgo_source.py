"""Free DuckDuckGo HTML Search provider for zero-key lead discovery."""

from __future__ import annotations

import logging
import re
from urllib.parse import unquote, urlparse
import httpx

from app.integrations.sources.base import LeadSource
from app.schemas.hunter import DiscoveredCompany, HunterCriteria

logger = logging.getLogger(__name__)


class DuckDuckGoSource(LeadSource):
    """Company discovery using free DuckDuckGo HTML search.
    
    Requires 0 API keys and 0 subscriptions. Allows instant live testing!
    """

    @property
    def name(self) -> str:
        return "duckduckgo"

    async def is_available(self) -> bool:
        return True

    async def search(self, criteria: HunterCriteria) -> list[DiscoveredCompany]:
        query = f"{criteria.industry} companies in {criteria.country}"
        logger.info("DuckDuckGoSource searching: '%s'", query)

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        try:
            async with httpx.AsyncClient(timeout=15.0, headers=headers) as client:
                response = await client.post(
                    "https://html.duckduckgo.com/html/",
                    data={"q": query},
                    follow_redirects=True,
                )
                html = response.text
        except Exception as e:
            logger.error("DuckDuckGoSource error: %s", e)
            return []

        companies: list[DiscoveredCompany] = []
        seen_domains = set()

        # Extract links from DDG HTML results: href="//duckduckgo.com/l/?uddg=URL&rut=1"
        matches = re.findall(r'<a class="result__url" href="([^"]+)">\s*([^<]+)</a>', html)
        if not matches:
            # Fallback regex for link patterns
            matches = re.findall(r'href=".*?uddg=([^"&]+).*?"[^>]*>(.*?)</a>', html)

        for raw_url, raw_text in matches:
            # Clean redirect wrapper if present
            clean_url = unquote(raw_url).strip()
            if "uddg=" in clean_url:
                clean_url = clean_url.split("uddg=")[-1].split("&")[0]

            if not clean_url.startswith("http"):
                clean_url = f"https://{clean_url}"

            try:
                parsed = urlparse(clean_url)
                domain = parsed.netloc.lower()
                if domain.startswith("www."):
                    domain = domain[4:]
            except Exception:
                continue

            if not domain or domain in seen_domains:
                continue

            # Filter search engines and social aggregators
            if any(agg in domain for agg in ["duckduckgo.com", "google.com", "bing.com", "linkedin.com", "facebook.com", "instagram.com", "wikipedia.org", "yelp.com", "yellowpages.com"]):
                continue

            seen_domains.add(domain)

            name = domain.split(".")[0].replace("-", " ").title()

            companies.append(
                DiscoveredCompany(
                    name=name,
                    domain=domain,
                    website_url=f"https://{domain}",
                    country=criteria.country,
                    industry=criteria.industry,
                    source="duckduckgo",
                    raw_data={"source_url": clean_url},
                )
            )

            if len(companies) >= criteria.max_companies:
                break

        return companies
