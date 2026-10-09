"""Message Event recording service."""

from sqlalchemy.ext.asyncio import AsyncSession
from app.models.message_event import MessageEvent
from app.models.message import Message

class MessageEventService:
    def __init__(self, db: AsyncSession):
        self.db = db
        
    async def record_event(self, message_id: str, event_type: str, event_data: dict = None) -> MessageEvent:
        """
        Record an event lifecycle state for a message.
        Examples: MESSAGE_SENT, MESSAGE_FAILED, MESSAGE_REJECTED
        """
        event = MessageEvent(
            message_id=message_id,
            event_type=event_type,
            event_data=event_data or {}
        )
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(event)
        return event
