"""Hunter.io enrichment provider for decision makers and email finding."""

from __future__ import annotations

import logging
import httpx

from app.integrations.enrichment.base import EnrichmentProvider
from app.schemas.hunter import DiscoveredCompany, DiscoveredPerson

logger = logging.getLogger(__name__)


class HunterEnrichmentProvider(EnrichmentProvider):
    """Enrichment and decision-maker contact discovery via Hunter.io API.
    
    Free tier offers 25 searches/month.
    """

    def __init__(self, api_key: str = "") -> None:
        self._api_key = api_key
        self._base_url = "https://api.hunter.io/v2"

    @property
    def name(self) -> str:
        return "hunter"

    async def is_available(self) -> bool:
        return bool(self._api_key)

    async def enrich_company(self, company: DiscoveredCompany) -> DiscoveredCompany:
        """Domain search via Hunter gives company pattern & name."""
        return company

    async def find_people(
        self, company: DiscoveredCompany, roles: list[str]
    ) -> list[DiscoveredPerson]:
        """Find people associated with domain using Hunter.io domain-search."""
        if not self._api_key or not company.domain:
            return []

        params = {
            "domain": company.domain,
            "api_key": self._api_key,
            "limit": 10,
        }

        people: list[DiscoveredPerson] = []

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                res = await client.get(f"{self._base_url}/domain-search", params=params)
                if res.status_code == 200:
                    data = res.json().get("data", {})
                    emails = data.get("emails", [])

                    for item in emails:
                        first_name = item.get("first_name") or ""
                        last_name = item.get("last_name") or ""
                        email = item.get("value") or ""
                        position = item.get("position") or ""
                        linkedin = item.get("linkedin") or ""

                        # Filter by role keywords if specified
                        if roles and position:
                            is_match = any(r.lower() in position.lower() for r in roles)
                            if not is_match:
                                continue

                        if not email and (not first_name and not last_name):
                            continue

                        people.append(
                            DiscoveredPerson(
                                first_name=first_name,
                                last_name=last_name,
                                title=position,
                                email=email,
                                linkedin_url=linkedin,
                                company_domain=company.domain,
                                is_decision_maker=True,
                                raw_source="hunter",
                            )
                        )
        except Exception as e:
            logger.warning("Hunter.io find_people failed for '%s': %s", company.domain, e)

        return people
