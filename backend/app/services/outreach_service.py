"""Outreach service coordinating sending emails."""

import logging
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update
from app.models.message import Message
from app.integrations.email.base import EmailProvider
from app.integrations.provider_errors import safe_provider_error

logger = logging.getLogger(__name__)

class OutreachService:
    def __init__(self, db: AsyncSession, email_provider: EmailProvider | None = None):
        self.db = db
        if email_provider is None:
            from app.integrations.email import get_email_provider
            self.provider = get_email_provider()
        else:
            self.provider = email_provider
        
    async def send_message(self, message: Message, to_email: str) -> str | None:
        """Claim and send an approved message once; return None if already claimed."""
        claim = await self.db.execute(
            update(Message)
            .where(Message.id == message.id, Message.status == "approved")
            .values(status="sending")
            .execution_options(synchronize_session=False)
        )
        await self.db.commit()
        if claim.rowcount != 1:
            await self.db.refresh(message)
            logger.info(
                "Skipping duplicate send attempt for message %s (status=%s).",
                message.id,
                message.status,
            )
            return None

        message.status = "sending"

        try:
            external_id = await self.provider.send_email(
                to_email=to_email,
                subject=message.subject,
                body=message.body
            )

            message.status = "sent"
            message.external_id = external_id
            message.sent_at = datetime.now(timezone.utc)
            await self.db.commit()

            return external_id

        except Exception as e:
            safe_error = safe_provider_error("email_delivery", e)
            logger.error(
                "Failed to send message %s (%s).",
                message.id,
                safe_error.error_type,
            )
            message.status = "failed"
            meta = message.metadata_ or {}
            meta["send_error"] = str(safe_error)
            message.metadata_ = meta
            await self.db.commit()
            raise
