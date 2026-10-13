"""Resend Email Provider for real outbound email sending."""

from __future__ import annotations

import logging
from typing import Optional
import httpx

from app.integrations.email.base import EmailProvider

logger = logging.getLogger(__name__)


class ResendEmailProvider(EmailProvider):
    """Real outbound email provider using Resend API.
    
    Free tier allows 3,000 emails/month (100 emails/day).
    Default from_email is onboarding@resend.dev (for testing) or user's verified custom domain.
    """

    def __init__(self, api_key: str = "", default_from_email: str = "onboarding@resend.dev") -> None:
        self._api_key = api_key
        self._default_from_email = default_from_email
        self._api_url = "https://api.resend.com/emails"

    @property
    def name(self) -> str:
        return "resend"

    async def is_available(self) -> bool:
        return bool(self._api_key)

    async def send_email(
        self, to_email: str, subject: str, body: str, from_email: Optional[str] = None
    ) -> str:
        if not self._api_key:
            raise ValueError("ResendEmailProvider: RESEND_API_KEY is not configured.")

        sender = from_email or self._default_from_email

        payload = {
            "from": sender,
            "to": [to_email],
            "subject": subject,
            "text": body,
        }

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        logger.info("Sending email via Resend to '%s' with subject '%s'", to_email, subject)

        async with httpx.AsyncClient(timeout=20.0) as client:
            res = await client.post(self._api_url, json=payload, headers=headers)
            if res.status_code not in (200, 201):
                logger.error("Resend API error [%d]: %s", res.status_code, res.text)
                raise RuntimeError(f"Resend send failed ({res.status_code}): {res.text}")

            data = res.json()
            message_id = data.get("id") or "resend-unknown-id"
            logger.info("Email delivered via Resend. Message ID: %s", message_id)
            return message_id
