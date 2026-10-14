"""VerificationService — coordinate email/contact verification.

Architecture
------------
    Hunter node (verify)
          ↓
    VerificationService          ← this file
          ↓
    VerificationProvider (ABC)
          ↓
    Real provider (ZeroBounce, NeverBounce, …) — injected in Phase 4+

Phase 3 ships with a MockVerificationProvider that marks every email as
VerificationStatus.unknown so the workflow can run end-to-end without
spending API credits.
"""

from __future__ import annotations

import logging

from app.integrations.verification.base import VerificationProvider
from app.integrations.provider_errors import ProviderConfigurationError
from app.schemas.hunter import VerificationResult, VerificationStatus

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Mock provider — used in Phase 3 / tests
# ---------------------------------------------------------------------------


class MockVerificationProvider(VerificationProvider):
    """No-op verification provider used during development and testing."""

    @property
    def name(self) -> str:
        return "mock_verification"

    async def is_available(self) -> bool:
        return True

    async def verify_email(self, email: str) -> VerificationResult:
        """Return status=unknown without making any API call."""
        logger.debug(
            "MockVerificationProvider: verify_email('%s') → unknown.", email
        )
        return VerificationResult(
            contact_value=email,
            status=VerificationStatus.unknown,
            confidence=0.0,
            provider=self.name,
            reason="mock_mode",
        )


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class VerificationService:
    """Application-level facade for contact verification."""

    def __init__(self, provider: VerificationProvider | None = None) -> None:
        self.mode = "injected" if provider is not None else "configured"
        if provider is not None:
            self._provider = provider
            return

        from app.services.integration_settings_service import get_runtime_settings
        settings = get_runtime_settings()

        selected = settings.VERIFICATION_PROVIDER.lower().strip()
        if selected == "mock":
            self._provider = MockVerificationProvider()
        elif selected == "hunter":
            if not settings.HUNTER_API_KEY:
                raise ProviderConfigurationError("Hunter verification is selected but has no API key.")
            from app.integrations.verification.hunter_verifier import HunterVerificationProvider
            self._provider = HunterVerificationProvider(api_key=settings.HUNTER_API_KEY)
        elif selected == "dns":
            from app.integrations.verification.dns_verifier import DnsVerificationProvider
            self._provider = DnsVerificationProvider()
        elif selected == "auto":
            if settings.HUNTER_API_KEY:
                from app.integrations.verification.hunter_verifier import HunterVerificationProvider
                self._provider = HunterVerificationProvider(api_key=settings.HUNTER_API_KEY)
            else:
                raise ProviderConfigurationError(
                    "Verification provider is auto but no real provider is configured; "
                    "select VERIFICATION_PROVIDER=mock for mock mode."
                )
        else:
            raise ProviderConfigurationError(
                f"Unsupported verification provider: {selected or 'empty'}."
            )
        self.mode = "mock" if isinstance(self._provider, MockVerificationProvider) else "real"

    @property
    def provider_name(self) -> str:
        return self._provider.name

    async def verify_email(self, email: str) -> VerificationResult:
        """Verify a single email address.

        Returns a VerificationResult with status=unknown if the provider
        is unavailable or the email is empty.
        """
        if not email:
            return VerificationResult(
                contact_value=email,
                status=VerificationStatus.skipped,
                reason="empty_email",
            )

        if not await self._provider.is_available():
            logger.warning(
                "VerificationProvider '%s' is unavailable – returning skipped.",
                self._provider.name,
            )
            return VerificationResult(
                contact_value=email,
                status=VerificationStatus.skipped,
                provider=self._provider.name,
                reason="provider_unavailable",
            )

        logger.debug(
            "Verifying '%s' via '%s'.", email, self._provider.name
        )
        return await self._provider.verify_email(email)
