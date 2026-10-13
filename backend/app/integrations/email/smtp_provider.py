"""SMTP Email Provider for standard SMTP / Gmail App Password."""

from __future__ import annotations

import asyncio
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging
import smtplib
from typing import Optional
import uuid

from app.integrations.email.base import EmailProvider

logger = logging.getLogger(__name__)


class SmtpEmailProvider(EmailProvider):
    """Outbound email provider via standard SMTP (Gmail App Password, Outlook, etc.).
    
    Zero third-party service required.
    """

    def __init__(
        self,
        host: str = "smtp.gmail.com",
        port: int = 465,
        user: str = "",
        password: str = "",
        from_email: str = "",
    ) -> None:
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.from_email = from_email or user

    @property
    def name(self) -> str:
        return "smtp"

    async def is_available(self) -> bool:
        return bool(self.host and self.user and self.password)

    def _sync_send(self, to_email: str, subject: str, body: str, sender: str) -> str:
        msg = MIMEMultipart()
        msg["From"] = sender
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        if self.port == 465:
            with smtplib.SMTP_SSL(self.host, self.port, timeout=15) as server:
                server.login(self.user, self.password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(self.host, self.port, timeout=15) as server:
                server.starttls()
                server.login(self.user, self.password)
                server.send_message(msg)

        return f"smtp-{uuid.uuid4().hex[:12]}"

    async def send_email(
        self, to_email: str, subject: str, body: str, from_email: Optional[str] = None
    ) -> str:
        if not self.user or not self.password:
            raise ValueError("SmtpEmailProvider: SMTP_USER and SMTP_PASSWORD required.")

        sender = from_email or self.from_email

        logger.info("Sending email via SMTP (%s) to '%s'", self.host, to_email)
        message_id = await asyncio.to_thread(self._sync_send, to_email, subject, body, sender)
        logger.info("Email delivered via SMTP. Message ID: %s", message_id)
        return message_id
