"""Outreach service coordinating sending emails."""

import logging
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.message import Message
from app.integrations.email.base import EmailProvider

logger = logging.getLogger(__name__)

class OutreachService:
    def __init__(self, db: AsyncSession, email_provider: EmailProvider):
        self.db = db
        self.provider = email_provider
        
    async def send_message(self, message: Message, to_email: str) -> str:
        """Execute the send via the configured provider."""
        message.status = "sending"
        await self.db.commit()
        
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
            logger.error(f"Failed to send message {message.id}: {e}")
            message.status = "failed"
            # Could store failure reason in metadata
            meta = message.metadata_ or {}
            meta["send_error"] = str(e)
            message.metadata_ = meta
            await self.db.commit()
            raise
