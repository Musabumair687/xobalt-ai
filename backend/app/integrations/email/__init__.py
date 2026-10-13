"""Email integrations package and factory."""

from __future__ import annotations

from typing import Optional
from app.integrations.email.base import EmailProvider


class MockEmailProvider(EmailProvider):
    """Fallback / Mock email provider for testing."""

    async def send_email(
        self, to_email: str, subject: str, body: str, from_email: Optional[str] = None
    ) -> str:
        import uuid
        return f"mock-{uuid.uuid4().hex[:12]}"


def get_email_provider() -> EmailProvider:
    """Instantiate configured email provider based on Settings."""
    from app.config import get_settings
    settings = get_settings()

    if settings.RESEND_API_KEY and settings.EMAIL_PROVIDER in ("auto", "resend"):
        from app.integrations.email.resend_provider import ResendEmailProvider
        return ResendEmailProvider(
            api_key=settings.RESEND_API_KEY,
            default_from_email=settings.RESEND_FROM_EMAIL,
        )

    if settings.SMTP_USER and settings.SMTP_PASSWORD and settings.EMAIL_PROVIDER in ("auto", "smtp"):
        from app.integrations.email.smtp_provider import SmtpEmailProvider
        return SmtpEmailProvider(
            host=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            user=settings.SMTP_USER,
            password=settings.SMTP_PASSWORD,
            from_email=settings.SMTP_FROM_EMAIL or settings.SMTP_USER,
        )

    return MockEmailProvider()
