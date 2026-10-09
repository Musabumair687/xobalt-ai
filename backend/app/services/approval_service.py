"""Service to manage Human Approval states for Messages."""

import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.message import Message

class ApprovalService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_message(self, message_id: uuid.UUID) -> Message | None:
        result = await self.db.execute(select(Message).where(Message.id == message_id))
        return result.scalars().first()

    async def process_approval(
        self, 
        message_id: uuid.UUID, 
        action: str, 
        edited_subject: str = None, 
        edited_body: str = None,
        reason: str = None
    ) -> Message:
        """Handle human review actions on a pending message."""
        msg = await self.get_message(message_id)
        if not msg:
            raise ValueError(f"Message {message_id} not found.")

        if action == "approve":
            msg.status = "approved"
        elif action == "edit":
            if edited_subject: msg.subject = edited_subject
            if edited_body: msg.body = edited_body
            msg.status = "approved"
        elif action == "reject":
            msg.status = "rejected"
            # Could store rejection reason in metadata
            meta = msg.metadata_ or {}
            meta["rejection_reason"] = reason
            msg.metadata_ = meta
        elif action == "regenerate":
            # Just push it back to draft state, workflow will catch it
            msg.status = "draft"
        else:
            raise ValueError(f"Unknown approval action: {action}")

        await self.db.commit()
        await self.db.refresh(msg)
        return msg
