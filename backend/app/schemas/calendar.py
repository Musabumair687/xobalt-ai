"""Schemas for Phase 9 Calendar and Booking."""
from datetime import datetime, timezone
from typing import Optional, List
from pydantic import BaseModel, Field

class TimeSlot(BaseModel):
    start_time: datetime
    end_time: datetime
    timezone: str = "UTC"

class AvailabilityRequest(BaseModel):
    start_date: datetime
    end_date: datetime
    duration_minutes: int = 30
    timezone: str = "UTC"

class BookingRequest(BaseModel):
    slot: TimeSlot
    lead_id: str
    calendar_id: str
    organization_id: str
    
class BookingResult(BaseModel):
    success: bool
    appointment_id: Optional[str] = None
    event_id: Optional[str] = None
    meeting_link: Optional[str] = None
    error: Optional[str] = None

class CalendarEvent(BaseModel):
    id: str
    title: str
    start_time: datetime
    end_time: datetime
    meeting_link: Optional[str] = None
    status: str
