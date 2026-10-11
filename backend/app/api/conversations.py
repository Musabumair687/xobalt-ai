"""API router for Conversations & Closer."""

import logging
from pydantic import BaseModel
from fastapi import APIRouter, Depends, BackgroundTasks, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.dependencies import get_db
from app.workers.inbox_worker import InboxWorker

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/conversations", tags=["Conversations & Closer"])

class IncomingEmailWebhook(BaseModel):
    sender_email: str
    subject: str
    content: str

@router.post("/webhook/email", status_code=status.HTTP_202_ACCEPTED)
async def email_webhook(
    webhook: IncomingEmailWebhook,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Webhook conceptually called by Gmail/provider when a new email arrives.
    """
    # Run sync for testing purposes, normally BackgroundTasks
    worker = InboxWorker(db)
    result = await worker.process_new_reply(webhook.sender_email, webhook.subject, webhook.content)
    
    return {"status": "processed", "result": result}
