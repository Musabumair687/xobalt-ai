"""API router for Appointments & Booking."""

import logging
import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.dependencies import get_db
from app.workers.calendar_worker import CalendarWorker
from app.schemas.calendar import AvailabilityRequest, BookingRequest
from app.models.conversation import Conversation
from app.models.user import User
from app.auth import get_current_user
from app.schemas.common import PaginatedResponse
from app.schemas.contracts import AppointmentListItem
from app.services.integration_settings_service import organization_settings_scope

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/calendar", tags=["Calendar & Appointments"])

@router.post("/availability", status_code=status.HTTP_200_OK)
async def get_availability(
    request: AvailabilityRequest,
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    await _require_owned_conversation(db, conversation_id, current_user.organization_id)
    worker = CalendarWorker(db)
    state = {
        "conversation_id": conversation_id,
        "action": "get_availability",
        "availability_request": request,
        "errors": []
    }
    async with organization_settings_scope(db, current_user.organization_id):
        result = await worker.run_booking_workflow(state)
    return {"available_slots": [s.model_dump() for s in result.get("available_slots", [])]}

@router.post("/book", status_code=status.HTTP_200_OK)
async def book_slot(
    request: BookingRequest,
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    conversation = await _require_owned_conversation(
        db,
        conversation_id,
        current_user.organization_id,
    )
    if (
        request.organization_id != current_user.organization_id
        or request.lead_id != conversation.lead_id
    ):
        raise HTTPException(status_code=404, detail="Conversation not found")
    worker = CalendarWorker(db)
    state = {
        "conversation_id": conversation_id,
        "action": "book_slot",
        "booking_request": request,
        "errors": []
    }
    async with organization_settings_scope(db, current_user.organization_id):
        result = await worker.run_booking_workflow(state)
    return result.get("booking_result", {"success": False, "error": "Unknown error"})

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from sqlalchemy import select, desc, func
from sqlalchemy.orm import selectinload, with_loader_criteria
from app.models.appointment import Appointment
from app.models.lead import Lead
from app.models.company import Company
from app.models.person import Person
from sqlalchemy.orm import selectinload


async def _require_owned_conversation(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    organization_id: uuid.UUID,
) -> Conversation:
    result = await db.execute(
        select(Conversation)
        .options(selectinload(Conversation.lead))
        .where(
            Conversation.id == conversation_id,
            Conversation.organization_id == organization_id,
        )
    )
    conversation = result.scalars().first()
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation

class CreateAppointmentDirectRequest(BaseModel):
    title: str = Field(default="Strategy & Demo Call", min_length=1, max_length=500)
    lead_id: Optional[uuid.UUID] = None
    attendee_name: Optional[str] = Field(default=None, max_length=255)
    attendee_email: Optional[str] = Field(
        default=None,
        max_length=320,
        pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$",
    )
    company_name: Optional[str] = Field(default=None, max_length=255)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    meeting_link: Optional[str] = Field(default=None, max_length=2048)
    notes: Optional[str] = Field(default=None, max_length=10000)

@router.get(
    "/appointments",
    response_model=PaginatedResponse[AppointmentListItem],
    summary="List scheduled appointments",
)
async def list_appointments(
    current_user: User = Depends(get_current_user),
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    db: AsyncSession = Depends(get_db),
):
    """Fetch one page of meetings/appointments with lead and attendee metadata."""
    stmt = (
        select(Appointment)
        .where(Appointment.organization_id == current_user.organization_id)
        .options(
            selectinload(Appointment.lead).selectinload(Lead.company),
            selectinload(Appointment.lead).selectinload(Lead.person),
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
        .order_by(desc(Appointment.start_time))
    )
    total = await db.scalar(
        select(func.count()).select_from(stmt.order_by(None).subquery())
    ) or 0
    res = await db.execute(stmt.offset((page - 1) * page_size).limit(page_size))
    appts = res.scalars().all()

    output = []
    for a in appts:
        lead = a.lead
        company = lead.company if lead else None
        person = lead.person if lead else None

        output.append({
            "id": str(a.id),
            "title": a.title,
            "description": a.description,
            "start_time": a.start_time.isoformat() if a.start_time else None,
            "end_time": a.end_time.isoformat() if a.end_time else None,
            "timezone": a.timezone,
            "status": a.status,
            "meeting_link": a.meeting_link,
            "location": a.location,
            "attendee_name": f"{person.first_name} {person.last_name}" if person else (a.metadata_ or {}).get("attendee_name", "Prospective Client"),
            "attendee_email": (a.metadata_ or {}).get("attendee_email", "client@company.com"),
            "company_name": company.name if company else (a.metadata_ or {}).get("company_name", "Target Account"),
        })

    return {
        "items": output,
        "page": page,
        "page_size": page_size,
        "total": total,
        "pages": (total + page_size - 1) // page_size,
    }

@router.post("/appointments", status_code=status.HTTP_201_CREATED, summary="Create an appointment directly")
async def create_appointment(
    payload: CreateAppointmentDirectRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Manually book or schedule an appointment."""
    from datetime import datetime, timedelta, timezone

    organization_id = current_user.organization_id
    lead_uuid = payload.lead_id
    if lead_uuid:
        lead_res = await db.execute(
            select(Lead.id).where(
                Lead.id == lead_uuid,
                Lead.organization_id == organization_id,
            )
        )
        if lead_res.scalar_one_or_none() is None:
            raise HTTPException(status_code=404, detail="Lead not found")
    else:
        comp = Company(
            organization_id=organization_id,
            name=payload.company_name or "Prospect Inc",
        )
        db.add(comp)
        await db.flush()
        lead = Lead(
            organization_id=organization_id,
            company_id=comp.id,
            status="qualified",
            score=85,
        )
        db.add(lead)
        await db.flush()
        lead_uuid = lead.id

    now = datetime.now(timezone.utc)
    st = payload.start_time or (now + timedelta(days=1, hours=2))
    et = payload.end_time or (st + timedelta(minutes=30))
    if et <= st:
        raise HTTPException(status_code=422, detail="end_time must be after start_time")

    appt = Appointment(
        organization_id=organization_id,
        lead_id=lead_uuid,
        title=payload.title,
        description=payload.notes or "Scheduled demo call via Xobalt AI",
        start_time=st,
        end_time=et,
        status="scheduled",
        meeting_link=payload.meeting_link,
        metadata_={
            "attendee_name": payload.attendee_name,
            "attendee_email": payload.attendee_email,
            "company_name": payload.company_name,
        }
    )
    db.add(appt)
    await db.commit()
    await db.refresh(appt)

    return {
        "id": str(appt.id),
        "title": appt.title,
        "start_time": appt.start_time.isoformat(),
        "status": appt.status,
        "meeting_link": appt.meeting_link
    }
