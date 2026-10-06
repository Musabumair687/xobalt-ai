"""Tests for EnrichmentService."""

import pytest
from unittest.mock import AsyncMock

from app.services.enrichment_service import EnrichmentService, MockEnrichmentProvider
from app.integrations.enrichment.base import EnrichmentProvider
from app.schemas.hunter import DiscoveredCompany, DiscoveredPerson


def _company(name="Test Co", domain="test.com") -> DiscoveredCompany:
    return DiscoveredCompany(name=name, domain=domain)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_enrich_company_mock_returns_same_company():
    svc = EnrichmentService()  # uses MockEnrichmentProvider
    company = _company()
    result = await svc.enrich_company(company)
    assert result.name == company.name
    assert result.domain == company.domain


@pytest.mark.asyncio
async def test_find_people_mock_returns_empty():
    svc = EnrichmentService()
    people = await svc.find_people(_company(), ["CEO", "Founder"])
    assert people == []


@pytest.mark.asyncio
async def test_enrich_company_with_real_provider():
    """If provider is injected and available, it is called."""
    enriched = _company(name="Enriched Co")
    provider = AsyncMock(spec=EnrichmentProvider)
    provider.name = "test_provider"
    provider.is_available = AsyncMock(return_value=True)
    provider.enrich_company = AsyncMock(return_value=enriched)

    svc = EnrichmentService(provider=provider)
    result = await svc.enrich_company(_company())
    assert result.name == "Enriched Co"
    provider.enrich_company.assert_called_once()


@pytest.mark.asyncio
async def test_enrich_skips_when_provider_unavailable():
    provider = AsyncMock(spec=EnrichmentProvider)
    provider.name = "offline"
    provider.is_available = AsyncMock(return_value=False)

    svc = EnrichmentService(provider=provider)
    original = _company()
    result = await svc.enrich_company(original)
    # Returns original unchanged
    assert result is original
    provider.enrich_company.assert_not_called()


@pytest.mark.asyncio
async def test_find_people_with_real_provider():
    people = [DiscoveredPerson(full_name="John Smith", email="john@test.com")]
    provider = AsyncMock(spec=EnrichmentProvider)
    provider.name = "test_provider"
    provider.is_available = AsyncMock(return_value=True)
    provider.find_people = AsyncMock(return_value=people)

    svc = EnrichmentService(provider=provider)
    result = await svc.find_people(_company(), ["CEO"])
    assert len(result) == 1
    assert result[0].full_name == "John Smith"
