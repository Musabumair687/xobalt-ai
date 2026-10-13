"""Apollo.io enrichment provider for decision makers and company data."""

from __future__ import annotations

import logging
from typing import Any
import httpx

from app.integrations.enrichment.base import EnrichmentProvider
from app.schemas.hunter import DiscoveredCompany, DiscoveredPerson

logger = logging.getLogger(__name__)


class ApolloEnrichmentProvider(EnrichmentProvider):
    """Enrichment and decision-maker contact discovery via Apollo.io API.
    
    Apollo.io free tier provides free email and person lookup credits monthly.
    """

    def __init__(self, api_key: str = "") -> None:
        self._api_key = api_key
        self._base_url = "https://api.apollo.io/v1"

    @property
    def name(self) -> str:
        return "apollo"

    async def is_available(self) -> bool:
        return bool(self._api_key)

    async def enrich_company(self, company: DiscoveredCompany) -> DiscoveredCompany:
        """Enrich company details (employee count, industry, description) via Apollo."""
        if not self._api_key or not company.domain:
            return company

        headers = {
            "Content-Type": "application/json",
            "X-Api-Key": self._api_key,
        }

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                res = await client.get(
                    f"{self._base_url}/organizations/enrich",
                    params={"domain": company.domain},
                    headers=headers,
                )
                if res.status_code == 200:
                    data = res.json()
                    org = data.get("organization") or {}

                    company.employee_count = org.get("estimated_num_employees") or company.employee_count
                    if not company.industry and org.get("industry"):
                        company.industry = org.get("industry")
                    if not company.description and org.get("short_description"):
                        company.description = org.get("short_description")
                    if org.get("linkedin_url"):
                        company.linkedin_url = org.get("linkedin_url")
        except Exception as e:
            logger.warning("Apollo company enrichment failed for '%s': %s", company.domain, e)

        return company

    async def find_people(
        self, company: DiscoveredCompany, roles: list[str]
    ) -> list[DiscoveredPerson]:
        """Find decision makers (CEO, Founder, etc.) for this company."""
        if not self._api_key or not company.domain:
            return []

        headers = {
            "Content-Type": "application/json",
            "X-Api-Key": self._api_key,
        }

        # Query Apollo people search
        payload: dict[str, Any] = {
            "q_organization_domains": f"{company.domain}\n",
            "organization_domains": [company.domain],
            "page": 1,
            "per_page": 5,
        }
        if roles:
            payload["person_titles"] = roles

        people: list[DiscoveredPerson] = []

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                res = await client.post(
                    f"{self._base_url}/mixed_people/search",
                    json=payload,
                    headers=headers,
                )
                if res.status_code == 200:
                    data = res.json()
                    raw_people = data.get("people") or data.get("contacts") or []

                    # If no people found with strict role filter, retry without role filter
                    if not raw_people and roles:
                        payload.pop("person_titles", None)
                        res_retry = await client.post(
                            f"{self._base_url}/mixed_people/search",
                            json=payload,
                            headers=headers,
                        )
                        if res_retry.status_code == 200:
                            data_retry = res_retry.json()
                            raw_people = data_retry.get("people") or data_retry.get("contacts") or []

                    for p in raw_people:
                        first_name = p.get("first_name", "")
                        last_name = p.get("last_name", "")
                        email = p.get("email") or ""
                        title = p.get("title") or ""
                        linkedin = p.get("linkedin_url") or ""

                        if not first_name and not last_name:
                            continue

                        people.append(
                            DiscoveredPerson(
                                first_name=first_name,
                                last_name=last_name,
                                title=title,
                                email=email,
                                linkedin_url=linkedin,
                                company_domain=company.domain,
                                is_decision_maker=True,
                                raw_source="apollo",
                            )
                        )
        except Exception as e:
            logger.warning("Apollo find_people failed for '%s': %s", company.domain, e)

        return people
