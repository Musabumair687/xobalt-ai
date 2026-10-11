"""Worker for orchestrating booking flows."""

import logging
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.calendar_service import CalendarService
from app.services.availability_service import AvailabilityService
from app.services.appointment_service import AppointmentService
from app.services.booking_service import BookingService
from app.workflows.booking_workflow import build_booking_graph

logger = logging.getLogger(__name__)

class CalendarWorker:
    def __init__(self, db: AsyncSession):
        self.db = db
        
    async def run_booking_workflow(self, state: dict) -> dict:
        """Run the Booking LangGraph workflow."""
        cal_svc = CalendarService()
        avail_svc = AvailabilityService()
        appt_svc = AppointmentService(self.db)
        booking_svc = BookingService(cal_svc, avail_svc, appt_svc)
        
        graph = build_booking_graph(self.db, booking_svc)
        final_state = await graph.ainvoke(state)
        
        return final_state
