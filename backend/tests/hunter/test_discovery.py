"""Tests for DiscoveryService."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from app.config import Settings

from app.services.discovery_service import DiscoveryService
from app.integrations.sources.base import LeadSource
from app.schemas.hunter import DiscoveredCompany, HunterCriteria
from app.integrations.provider_errors import ProviderConfigurationError, ProviderRequestError
import uuid


@pytest.fixture(autouse=True)
def force_explicit_mock_mode(monkeypatch):
    monkeypatch.setattr(
        "app.config.get_settings",
        lambda: Settings(
            DISCOVERY_PROVIDER="mock",
            ENRICHMENT_PROVIDER="mock",
            VERIFICATION_PROVIDER="mock",
        ),
    )


def _criteria(**kwargs) -> HunterCriteria:
    defaults = dict(
        organization_id=uuid.uuid4(),
        industry="Real Estate",
        country="US",
        max_companies=10,
    )
    defaults.update(kwargs)
    return HunterCriteria(**defaults)


def _make_source(name: str, available: bool, results: list) -> LeadSource:
    """Build a mock LeadSource."""
    source = AsyncMock(spec=LeadSource)
    source.name = name
    source.is_available = AsyncMock(return_value=available)
    source.search = AsyncMock(return_value=results)
    return source


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_discovery_uses_available_source():
    companies = [DiscoveredCompany(name="Test Co", domain="test.com")]
    source = _make_source("mock", True, companies)
    svc = DiscoveryService(sources=[source])

    result = await svc.search(_criteria())
    assert len(result) == 1
    assert result[0].name == "Test Co"


@pytest.mark.asyncio
async def test_discovery_fails_explicitly_when_selected_source_unavailable():
    source = _make_source("unavailable", False, [])
    svc = DiscoveryService(sources=[source])

    with pytest.raises(ProviderConfigurationError, match="unavailable"):
        await svc.search(_criteria())
    assert svc.last_provider_status[0]["status"] == "failed"
    source.search.assert_not_called()


@pytest.mark.asyncio
async def test_discovery_aggregates_multiple_sources():
    source_a = _make_source("A", True, [DiscoveredCompany(name="Co A", domain="a.com")])
    source_b = _make_source("B", True, [DiscoveredCompany(name="Co B", domain="b.com")])
    svc = DiscoveryService(sources=[source_a, source_b])

    result = await svc.search(_criteria(max_companies=10))
    assert len(result) == 2


@pytest.mark.asyncio
async def test_discovery_respects_max_companies():
    companies = [DiscoveredCompany(name=f"Co {i}", domain=f"co{i}.com") for i in range(20)]
    source = _make_source("big", True, companies)
    svc = DiscoveryService(sources=[source])

    result = await svc.search(_criteria(max_companies=5))
    assert len(result) == 5


@pytest.mark.asyncio
async def test_discovery_provider_error_is_not_empty_success():
    source = AsyncMock(spec=LeadSource)
    source.name = "erroring"
    source.is_available = AsyncMock(return_value=True)
    source.search = AsyncMock(side_effect=RuntimeError("API down"))
    svc = DiscoveryService(sources=[source])

    with pytest.raises(ProviderRequestError):
        await svc.search(_criteria())
    assert svc.last_provider_status == [
        {
            "provider": "erroring",
            "status": "failed",
            "error": "ProviderRequestError",
            "error_type": "RuntimeError",
        }
    ]


@pytest.mark.asyncio
async def test_discovery_empty_mock_result_is_successful_empty_result():
    """Explicit mock mode may successfully return no candidates."""
    svc = DiscoveryService()
    result = await svc.search(_criteria())
    assert isinstance(result, list)
    assert result == []
    assert svc.mode == "mock"
    assert svc.last_provider_status[0]["status"] == "succeeded"
