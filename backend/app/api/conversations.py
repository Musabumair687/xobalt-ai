"""API router for Conversations & Closer."""

import logging
from pydantic import BaseModel
from fastapi import APIRouter, Depends, BackgroundTasks, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.dependencies import get_db
from app.workers.inbox_worker import InboxWorker

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/conversations", tags=["Conversations & Closer"])

from typing import Optional
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload
from app.models.message import Message
from app.models.lead import Lead
from app.models.person import Person
from app.models.company import Company
from app.models.contact import Contact

@router.get("/messages", summary="List all outbound and drafted messages for Inbox review")
async def list_messages(
    status_filter: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Retrieve all outreach messages across campaigns for human approval and delivery."""
    stmt = (
        select(Message)
        .options(
            selectinload(Message.lead).selectinload(Lead.company),
            selectinload(Message.lead).selectinload(Lead.person).selectinload(Person.contacts),
        )
        .order_by(desc(Message.created_at))
    )

    if status_filter and status_filter != "all":
        stmt = stmt.where(Message.status == status_filter)

    res = await db.execute(stmt)
    messages = res.scalars().all()

    output = []
    for m in messages:
        lead = m.lead
        company = lead.company if lead else None
        person = lead.person if lead else None

        email = None
        if person and person.contacts:
            for c in person.contacts:
                if c.type == "email":
                    email = c.value
                    break

        output.append({
            "id": str(m.id),
            "lead_id": str(lead.id) if lead else None,
            "subject": m.subject,
            "body": m.body,
            "status": m.status,
            "sent_at": m.sent_at.isoformat() if m.sent_at else None,
            "created_at": m.created_at.isoformat() if m.created_at else None,
            "recipient_name": f"{person.first_name} {person.last_name}" if person else "Executive",
            "recipient_title": person.title if person else "Decision Maker",
            "recipient_email": email or (f"contact@{company.domain}" if company and company.domain else None),
            "company_name": company.name if company else "Target Company",
            "company_domain": company.domain if company else None,
            "lead_score": lead.score if lead else None,
        })

    return output


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
    worker = InboxWorker(db)
    result = await worker.process_new_reply(webhook.sender_email, webhook.subject, webhook.content)
    return {"status": "processed", "result": result}


