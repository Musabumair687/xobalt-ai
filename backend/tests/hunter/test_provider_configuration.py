"""Provider selection and failure contracts, without live network calls."""

from __future__ import annotations

import httpx
import pytest

from app.config import Settings
from app.integrations.enrichment.apollo import ApolloEnrichmentProvider
from app.integrations.email import get_email_provider
from app.integrations.email.resend_provider import ResendEmailProvider
from app.integrations.provider_errors import (
    ProviderConfigurationError,
    ProviderRequestError,
)
from app.integrations.sources.tavily_source import TavilySource
from app.integrations.verification.hunter_verifier import HunterVerificationProvider
from app.services.discovery_service import DiscoveryService
from app.services.enrichment_service import EnrichmentService
from app.services.verification_service import VerificationService
from app.schemas.hunter import HunterCriteria


def test_explicit_real_provider_selection_uses_real_adapters(monkeypatch):
    monkeypatch.setattr(
        "app.config.get_settings",
        lambda: Settings(
            DISCOVERY_PROVIDER="serpapi",
            SERPAPI_API_KEY="test-serp-key",
            ENRICHMENT_PROVIDER="apollo",
            APOLLO_API_KEY="test-apollo-key",
            VERIFICATION_PROVIDER="hunter",
            HUNTER_API_KEY="test-hunter-key",
            EMAIL_PROVIDER="resend",
            RESEND_API_KEY="test-resend-key",
        ),
    )

    discovery = DiscoveryService()
    enrichment = EnrichmentService()
    verification = VerificationService()
    email = get_email_provider()

    assert discovery.mode == "real"
    assert discovery.provider_name == "search_source:serpapi"
    assert isinstance(enrichment._provider, ApolloEnrichmentProvider)
    assert isinstance(verification._provider, HunterVerificationProvider)
    assert isinstance(email, ResendEmailProvider)


def test_real_provider_without_required_key_does_not_fall_back_to_mock(monkeypatch):
    monkeypatch.setattr(
        "app.config.get_settings",
        lambda: Settings(DISCOVERY_PROVIDER="tavily", TAVILY_API_KEY=""),
    )

    with pytest.raises(ProviderConfigurationError, match="no API key"):
        DiscoveryService()


@pytest.mark.asyncio
async def test_tavily_http_failure_is_not_returned_as_no_results(monkeypatch):
    original_async_client = httpx.AsyncClient
    transport = httpx.MockTransport(
        lambda request: httpx.Response(503, request=request)
    )

    def mocked_client(*args, **kwargs):
        return original_async_client(transport=transport, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", mocked_client)
    source = TavilySource(api_key="test-provider-secret")
    criteria = HunterCriteria(
        organization_id="3db4fbe0-b420-4dc0-8d91-00bcaa218330",
        industry="Real Estate",
        country="US",
    )

    with pytest.raises(ProviderRequestError) as error:
        await source.search(criteria)

    assert error.value.error_type == "HTTPStatusError"
    assert "test-provider-secret" not in str(error.value)
