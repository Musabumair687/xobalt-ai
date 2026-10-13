"""API router for Appointments & Booking."""

import logging
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.dependencies import get_db
from app.workers.calendar_worker import CalendarWorker
from app.schemas.calendar import AvailabilityRequest, BookingRequest

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/calendar", tags=["Calendar & Appointments"])

@router.post("/availability", status_code=status.HTTP_200_OK)
async def get_availability(
    request: AvailabilityRequest,
    conversation_id: str,
    db: AsyncSession = Depends(get_db)
):
    worker = CalendarWorker(db)
    state = {
        "conversation_id": conversation_id,
        "action": "get_availability",
        "availability_request": request,
        "errors": []
    }
    result = await worker.run_booking_workflow(state)
    return {"available_slots": [s.model_dump() for s in result.get("available_slots", [])]}

@router.post("/book", status_code=status.HTTP_200_OK)
async def book_slot(
    request: BookingRequest,
    conversation_id: str,
    db: AsyncSession = Depends(get_db)
):
    worker = CalendarWorker(db)
    state = {
        "conversation_id": conversation_id,
        "action": "book_slot",
        "booking_request": request,
        "errors": []
    }
    result = await worker.run_booking_workflow(state)
    return result.get("booking_result", {"success": False, "error": "Unknown error"})

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload
from app.models.appointment import Appointment
from app.models.lead import Lead
from app.models.company import Company
from app.models.person import Person
from app.models.organization import Organization

class CreateAppointmentDirectRequest(BaseModel):
    title: str = Field(default="Strategy & Demo Call")
    lead_id: Optional[str] = None
    attendee_name: Optional[str] = None
    attendee_email: Optional[str] = None
    company_name: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    meeting_link: Optional[str] = Field(default="https://meet.google.com/xob-live-rev")
    notes: Optional[str] = None

@router.get("/appointments", summary="List all scheduled appointments")
async def list_appointments(db: AsyncSession = Depends(get_db)):
    """Fetch all meetings/appointments with lead and attendee metadata."""
    stmt = (
        select(Appointment)
        .options(
            selectinload(Appointment.lead).selectinload(Lead.company),
            selectinload(Appointment.lead).selectinload(Lead.person),
        )
        .order_by(desc(Appointment.start_time))
    )
    res = await db.execute(stmt)
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

    return output

@router.post("/appointments", status_code=status.HTTP_201_CREATED, summary="Create an appointment directly")
async def create_appointment(payload: CreateAppointmentDirectRequest, db: AsyncSession = Depends(get_db)):
    """Manually book or schedule an appointment."""
    import uuid
    from datetime import datetime, timedelta, timezone

    org_res = await db.execute(select(Organization).limit(1))
    org = org_res.scalars().first()
    if not org:
        org = Organization(name="Default Workspace", slug="default-workspace")
        db.add(org)
        await db.flush()

    lead_uuid = None
    if payload.lead_id:
        try:
            lead_uuid = uuid.UUID(payload.lead_id)
        except Exception:
            pass

    if not lead_uuid:
        # Pick the latest lead or create a placeholder lead
        lead_res = await db.execute(select(Lead).limit(1))
        latest_lead = lead_res.scalars().first()
        if latest_lead:
            lead_uuid = latest_lead.id
        else:
            # Create a company and lead
            comp = Company(organization_id=org.id, name=payload.company_name or "Prospect Inc", domain="prospect.com")
            db.add(comp)
            await db.flush()
            lead = Lead(organization_id=org.id, company_id=comp.id, status="qualified", score=85)
            db.add(lead)
            await db.flush()
            lead_uuid = lead.id

    now = datetime.now(timezone.utc)
    st = payload.start_time or (now + timedelta(days=1, hours=2))
    et = payload.end_time or (st + timedelta(minutes=30))

    appt = Appointment(
        organization_id=org.id,
        lead_id=lead_uuid,
        title=payload.title,
        description=payload.notes or "Scheduled demo call via Xobalt AI",
        start_time=st,
        end_time=et,
        status="scheduled",
        meeting_link=payload.meeting_link or "https://meet.google.com/xob-live-rev",
        metadata_={
            "attendee_name": payload.attendee_name or "Prospective Client",
            "attendee_email": payload.attendee_email or "client@company.com",
            "company_name": payload.company_name or "Target Account",
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

