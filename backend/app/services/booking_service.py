"""High level booking service orchestrating calendar, availability, and DB."""

import uuid
import logging
from typing import List
from datetime import datetime
from app.services.calendar_service import CalendarService
from app.services.availability_service import AvailabilityService
from app.services.appointment_service import AppointmentService
from app.schemas.calendar import BookingRequest, BookingResult, AvailabilityRequest, TimeSlot

logger = logging.getLogger(__name__)

class BookingService:
    def __init__(
        self,
        calendar_svc: CalendarService,
        avail_svc: AvailabilityService,
        appt_svc: AppointmentService
    ):
        self.calendar_svc = calendar_svc
        self.avail_svc = avail_svc
        self.appt_svc = appt_svc
        
    async def get_available_slots(self, request: AvailabilityRequest, calendar_id: str) -> List[TimeSlot]:
        """Return available slots for the given request and calendar."""
        candidates = self.avail_svc.generate_candidate_slots(request)
        busy_slots = await self.calendar_svc.get_availability(
            calendar_id, request.start_date, request.end_date
        )
        available = self.avail_svc.find_available_slots(candidates, busy_slots)
        return available
        
    async def book_meeting(self, request: BookingRequest, conv_id: uuid.UUID, title: str, attendees: List[str]) -> BookingResult:
        """Book a meeting for the selected slot, verifying availability again."""
        # Re-check availability exactly for this slot
        busy_slots = await self.calendar_svc.get_availability(
            request.calendar_id, request.slot.start_time, request.slot.end_time
        )
        available = self.avail_svc.find_available_slots([request.slot], busy_slots)
        
        if not available:
            logger.warning(f"Double booking prevented for {request.slot}")
            return BookingResult(success=False, error="Slot is no longer available.")
            
        # Create External Event
        event = await self.calendar_svc.create_event(
            calendar_id=request.calendar_id,
            title=title,
            start_time=request.slot.start_time,
            end_time=request.slot.end_time,
            attendee_emails=attendees
        )
        
        # Save Appointment
        appt = await self.appt_svc.create_appointment(
            org_id=request.organization_id,
            lead_id=request.lead_id,
            conv_id=conv_id,
            event=event,
            timezone=request.slot.timezone
        )
        
        return BookingResult(
            success=True,
            appointment_id=str(appt.id),
            event_id=event.id,
            meeting_link=event.meeting_link
        )
