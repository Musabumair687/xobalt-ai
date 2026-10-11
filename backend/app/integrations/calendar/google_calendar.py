"""Google Calendar Integration (Stubbed for MVP)."""

import uuid
from typing import List, Optional
from datetime import datetime, timedelta
from app.integrations.calendar.base import CalendarProvider
from app.schemas.calendar import TimeSlot, CalendarEvent

class GoogleCalendarProvider(CalendarProvider):
    @property
    def name(self) -> str:
        return "google_calendar"
        
    async def get_busy_slots(self, calendar_id: str, start_time: datetime, end_time: datetime) -> List[TimeSlot]:
        # For Phase 9 MVP testing, simulate one busy slot per day at 12 PM UTC
        busy = []
        current = start_time
        while current < end_time:
            busy.append(TimeSlot(
                start_time=current.replace(hour=12, minute=0, second=0, microsecond=0),
                end_time=current.replace(hour=13, minute=0, second=0, microsecond=0),
                timezone="UTC"
            ))
            current += timedelta(days=1)
        return busy
        
    async def create_event(
        self,
        calendar_id: str,
        title: str,
        start_time: datetime,
        end_time: datetime,
        attendee_emails: List[str],
        description: Optional[str] = None
    ) -> CalendarEvent:
        event_id = f"gcal_{uuid.uuid4().hex[:12]}"
        return CalendarEvent(
            id=event_id,
            title=title,
            start_time=start_time,
            end_time=end_time,
            meeting_link=f"https://meet.google.com/{uuid.uuid4().hex[:10]}",
            status="confirmed"
        )
        
    async def cancel_event(self, calendar_id: str, event_id: str) -> bool:
        return True
