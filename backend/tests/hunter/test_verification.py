"""Tests for VerificationService."""

import pytest
from unittest.mock import AsyncMock

from app.services.verification_service import VerificationService, MockVerificationProvider
from app.integrations.verification.base import VerificationProvider
from app.schemas.hunter import VerificationStatus


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mock_provider_returns_unknown():
    svc = VerificationService()  # uses MockVerificationProvider
    result = await svc.verify_email("john@example.com")
    assert result.contact_value == "john@example.com"
    assert result.status == VerificationStatus.unknown
    assert result.provider == "mock_verification"


@pytest.mark.asyncio
async def test_verify_empty_email_returns_skipped():
    svc = VerificationService()
    result = await svc.verify_email("")
    assert result.status == VerificationStatus.skipped


@pytest.mark.asyncio
async def test_verify_with_real_provider_valid():
    from app.schemas.hunter import VerificationResult
    vr = VerificationResult(
        contact_value="ceo@goodco.com",
        status=VerificationStatus.valid,
        confidence=0.99,
        provider="test_verifier",
    )
    provider = AsyncMock(spec=VerificationProvider)
    provider.name = "test_verifier"
    provider.is_available = AsyncMock(return_value=True)
    provider.verify_email = AsyncMock(return_value=vr)

    svc = VerificationService(provider=provider)
    result = await svc.verify_email("ceo@goodco.com")
    assert result.status == VerificationStatus.valid
    assert result.confidence == 0.99


@pytest.mark.asyncio
async def test_verify_skips_when_provider_unavailable():
    provider = AsyncMock(spec=VerificationProvider)
    provider.name = "offline"
    provider.is_available = AsyncMock(return_value=False)

    svc = VerificationService(provider=provider)
    result = await svc.verify_email("test@example.com")
    assert result.status == VerificationStatus.skipped
    provider.verify_email.assert_not_called()


@pytest.mark.asyncio
async def test_verify_with_invalid_email():
    from app.schemas.hunter import VerificationResult
    vr = VerificationResult(
        contact_value="bad@email.xyz",
        status=VerificationStatus.invalid,
        confidence=0.95,
        provider="test_verifier",
    )
    provider = AsyncMock(spec=VerificationProvider)
    provider.name = "test_verifier"
    provider.is_available = AsyncMock(return_value=True)
    provider.verify_email = AsyncMock(return_value=vr)

    svc = VerificationService(provider=provider)
    result = await svc.verify_email("bad@email.xyz")
    assert result.status == VerificationStatus.invalid
