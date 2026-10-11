"""Service to manage Appointments in DB."""

import uuid
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.appointment import Appointment
from app.schemas.calendar import CalendarEvent

logger = logging.getLogger(__name__)

class AppointmentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        
    async def create_appointment(
        self,
        org_id: uuid.UUID,
        lead_id: uuid.UUID,
        conv_id: uuid.UUID,
        event: CalendarEvent,
        timezone: str
    ) -> Appointment:
        """Create DB record from Calendar event."""
        appt = Appointment(
            organization_id=org_id,
            lead_id=lead_id,
            conversation_id=conv_id,
            title=event.title,
            start_time=event.start_time,
            end_time=event.end_time,
            timezone=timezone,
            calendar_event_id=event.id,
            meeting_link=event.meeting_link,
            status="CONFIRMED"
        )
        self.db.add(appt)
        await self.db.commit()
        await self.db.refresh(appt)
        return appt
        
    async def cancel_appointment(self, appointment_id: uuid.UUID) -> bool:
        """Mark appointment as cancelled in DB."""
        res = await self.db.execute(select(Appointment).where(Appointment.id == appointment_id))
        appt = res.scalars().first()
        if appt:
            appt.status = "CANCELLED"
            await self.db.commit()
            return True
        return False
