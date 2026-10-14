"""Schemas for Phase 9 Calendar and Booking."""
import uuid
from datetime import datetime, timezone
from typing import Optional, List
from pydantic import BaseModel, Field, model_validator

class TimeSlot(BaseModel):
    start_time: datetime
    end_time: datetime
    timezone: str = Field(default="UTC", min_length=1, max_length=100)

    @model_validator(mode="after")
    def validate_time_range(self):
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")
        return self

class AvailabilityRequest(BaseModel):
    start_date: datetime
    end_date: datetime
    duration_minutes: int = Field(default=30, ge=5, le=480)
    timezone: str = Field(default="UTC", min_length=1, max_length=100)

    @model_validator(mode="after")
    def validate_search_range(self):
        if self.end_date <= self.start_date:
            raise ValueError("end_date must be after start_date")
        return self

class BookingRequest(BaseModel):
    slot: TimeSlot
    lead_id: uuid.UUID
    calendar_id: str = Field(min_length=1, max_length=255)
    organization_id: uuid.UUID
    
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
