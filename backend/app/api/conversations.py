"""API router for Conversations & Closer."""

import logging
from typing import Annotated, Any, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.dependencies import get_db
from app.workers.inbox_worker import InboxWorker

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/conversations", tags=["Conversations & Closer"])

from sqlalchemy import select, desc, func
from sqlalchemy.orm import selectinload, with_loader_criteria
from app.models.message import Message
from app.models.lead import Lead
from app.models.person import Person
from app.models.company import Company
from app.models.user import User
from app.auth import get_current_user
from pydantic import Field
from app.schemas.common import PaginatedResponse
from app.schemas.contracts import MessageListItem

@router.get(
    "/messages",
    response_model=PaginatedResponse[MessageListItem],
    summary="List outbound and drafted messages for Inbox review",
)
async def list_messages(
    status_filter: Annotated[Optional[str], Query(max_length=50)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve all outreach messages across campaigns for human approval and delivery."""
    stmt = (
        select(Message)
        .where(Message.organization_id == current_user.organization_id)
        .options(
            selectinload(Message.lead).selectinload(Lead.company),
            selectinload(Message.lead).selectinload(Lead.person).selectinload(Person.contacts),
            with_loader_criteria(
                Lead,
                Lead.organization_id == current_user.organization_id,
                include_aliases=True,
            ),
            with_loader_criteria(
                Company,
                Company.organization_id == current_user.organization_id,
                include_aliases=True,
            ),
            with_loader_criteria(
                Person,
                Person.organization_id == current_user.organization_id,
                include_aliases=True,
            ),
        )
        .order_by(desc(Message.created_at))
    )

    if status_filter and status_filter != "all":
        stmt = stmt.where(Message.status == status_filter)

    total = await db.scalar(
        select(func.count()).select_from(stmt.order_by(None).subquery())
    ) or 0
    res = await db.execute(stmt.offset((page - 1) * page_size).limit(page_size))
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
            "recipient_title": (person.title or "Decision Maker") if person else "Decision Maker",
            "recipient_email": email or (f"contact@{company.domain}" if company and company.domain else None),
            "company_name": company.name if company else "Target Company",
            "company_domain": company.domain if company else None,
            "lead_score": lead.score if lead else None,
        })

    return {
        "items": output,
        "page": page,
        "page_size": page_size,
        "total": total,
        "pages": (total + page_size - 1) // page_size,
    }


class IncomingEmailWebhook(BaseModel):
    sender_email: str = Field(
        min_length=3,
        max_length=320,
        pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$",
    )
    subject: str = Field(min_length=1, max_length=998)
    content: str = Field(min_length=1, max_length=100000)

@router.post("/webhook/email", status_code=status.HTTP_202_ACCEPTED)
async def email_webhook(
    webhook: IncomingEmailWebhook,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    worker = InboxWorker(db)
    result = await worker.process_new_reply(
        webhook.sender_email,
        webhook.subject,
        webhook.content,
        current_user.organization_id,
    )
    return {"status": "processed", "result": result}
