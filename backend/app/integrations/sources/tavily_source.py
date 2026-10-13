"""Tavily search provider for lead discovery."""

from __future__ import annotations

import logging
from urllib.parse import urlparse
import httpx

from app.integrations.sources.base import LeadSource
from app.schemas.hunter import DiscoveredCompany, HunterCriteria

logger = logging.getLogger(__name__)


class TavilySource(LeadSource):
    """Company discovery via Tavily Search API.
    
    Tavily is optimized for LLMs and AI agents, returning clean, relevant web results.
    Free tier offers 1,000 requests/month.
    """

    def __init__(self, api_key: str = "") -> None:
        self._api_key = api_key

    @property
    def name(self) -> str:
        return "tavily"

    async def is_available(self) -> bool:
        return bool(self._api_key)

    async def search(self, criteria: HunterCriteria) -> list[DiscoveredCompany]:
        if not self._api_key:
            logger.warning("TavilySource: no API key configured.")
            return []

        # Formulate query strictly targeting commercial company sites rather than educational articles/guides
        location = criteria.country
        industry = criteria.industry
        query = f'"{industry}" ("solutions" OR "platform" OR "services" OR "company" OR "agency") "{location}" -wiki -list -top10 -largest -blog -article -news -"what is" -"advantages" -"examples" -faq'
        
        logger.info("TavilySource searching: '%s'", query)

        url = "https://api.tavily.com/search"
        payload = {
            "api_key": self._api_key,
            "query": query,
            "search_depth": "basic",
            "max_results": min(criteria.max_companies * 4, 30),
            "include_domains": [],
        }

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
        except Exception as e:
            logger.error("TavilySource HTTP error: %s", e)
            return []

        companies: list[DiscoveredCompany] = []
        seen_domains = set()

        # Extensive non-commercial & educational aggregator blacklist
        bad_domains = [
            "linkedin.com", "facebook.com", "instagram.com", "twitter.com",
            "wikipedia.org", "yelp.com", "yellowpages.com", "usnews.com",
            "mordorintelligence.com", "beckersdental.com", "dentistrytoday.com",
            "goodfirms.co", "f6s.com", "forbes.com", "statista.com", "reddit.com",
            "youtube.com", "quora.com", "glassdoor.com", "indeed.com", "clutch.co",
            "netsuite.com", "oracle.com", "8x8.com", "salesforce.com", "microsoft.com",
            "ibm.com", "hubspot.com", "ellucian.com", "investopedia.com", "techtarget.com",
            "medium.com", "substack.com", "businesswire.com", "prnewswire.com",
            "gartner.com", "g2.com", "capterra.com", "trustradius.com"
        ]

        bad_paths = [
            "/blog", "/article", "/articles", "/news", "/learn", "/resource",
            "/resources", "/post", "/posts", "/faq", "/guide", "/glossary",
            "/what-is", "/insights", "/press", "/events", "/docs", "/support"
        ]

        bad_title_cues = [
            "what is", "how to", "how does", "advantages", "examples", "faqs",
            "guide", "overview", "definition", "trends in", "vs ", "?",
            "reasons to", "everything you need", "top 10", "top 5", "ranked",
            "best places", "chains from", "largest "
        ]

        for item in data.get("results", []):
            link = item.get("url", "")
            title = item.get("title", "")
            snippet = item.get("content", "")

            try:
                parsed = urlparse(link)
                domain = parsed.netloc.lower()
                if domain.startswith("www."):
                    domain = domain[4:]
            except Exception:
                continue

            if not domain or domain in seen_domains:
                continue

            # 1. Filter out government, educational, or org domains
            if any(domain.endswith(tld) or f".{tld}." in domain for tld in ["gov", "govt", "edu", "mil"]):
                continue

            # 2. Filter out known content aggregators and mega-enterprises
            if any(agg in domain for agg in bad_domains):
                continue

            # 3. Filter out blog and resource paths
            path_lower = parsed.path.lower()
            if any(bp in path_lower for bp in bad_paths):
                continue

            # 4. Filter out article-style titles
            lower_title = title.lower()
            if any(bad in lower_title for bad in bad_title_cues):
                continue

            seen_domains.add(domain)

            # 5. Extract clean business name
            # Strip standard separators
            clean_name = title.split(" - ")[0].split(" | ")[0].split(" : ")[0].split(" – ")[0].strip()
            # If still looks like a sentence or is too long, derive from domain
            if len(clean_name) > 35 or len(clean_name.split()) > 5:
                # e.g. "kiwisaas.co.nz" -> "Kiwisaas"
                base_part = domain.split(".")[0].replace("-", " ")
                clean_name = base_part.title()

            companies.append(
                DiscoveredCompany(
                    name=clean_name or domain,
                    domain=domain,
                    website_url=f"https://{domain}",
                    country=criteria.country,
                    industry=criteria.industry,
                    source="tavily",
                    raw_data={"snippet": snippet[:200], "source_url": link},
                )
            )

            if len(companies) >= criteria.max_companies:
                break

        return companies

