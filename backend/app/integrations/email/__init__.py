"""Email integrations package and factory."""

from __future__ import annotations

from typing import Optional
from app.integrations.email.base import EmailProvider
from app.integrations.provider_errors import ProviderConfigurationError


class MockEmailProvider(EmailProvider):
    """Fallback / Mock email provider for testing."""

    async def send_email(
        self, to_email: str, subject: str, body: str, from_email: Optional[str] = None
    ) -> str:
        import uuid
        return f"mock-{uuid.uuid4().hex[:12]}"


def get_email_provider(settings=None) -> EmailProvider:
    """Instantiate configured email provider based on Settings."""
    if settings is None:
        from app.services.integration_settings_service import get_runtime_settings
        settings = get_runtime_settings()

    selected = settings.EMAIL_PROVIDER.lower().strip()
    if selected == "mock":
        return MockEmailProvider()

    if selected in ("auto", "resend") and settings.RESEND_API_KEY:
        from app.integrations.email.resend_provider import ResendEmailProvider
        return ResendEmailProvider(
            api_key=settings.RESEND_API_KEY,
            default_from_email=settings.RESEND_FROM_EMAIL,
        )

    if selected in ("auto", "smtp") and settings.SMTP_USER and settings.SMTP_PASSWORD:
        from app.integrations.email.smtp_provider import SmtpEmailProvider
        return SmtpEmailProvider(
            host=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            user=settings.SMTP_USER,
            password=settings.SMTP_PASSWORD,
            from_email=settings.SMTP_FROM_EMAIL or settings.SMTP_USER,
        )

    if selected == "resend":
        raise ProviderConfigurationError("Resend is selected but has no API key.")
    if selected == "smtp":
        raise ProviderConfigurationError("SMTP is selected but is missing credentials.")
    if selected == "auto":
        raise ProviderConfigurationError(
            "Email provider is auto but no real provider is configured; "
            "select EMAIL_PROVIDER=mock for mock mode."
        )
    raise ProviderConfigurationError(f"Unsupported email provider: {selected or 'empty'}.")
