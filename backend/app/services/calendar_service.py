"""Calendar Service for Provider Abstraction."""

import logging
from typing import List, Optional
from datetime import datetime
from app.integrations.calendar.base import CalendarProvider
from app.integrations.calendar.google_calendar import GoogleCalendarProvider
from app.schemas.calendar import TimeSlot, CalendarEvent

logger = logging.getLogger(__name__)

class CalendarService:
    def __init__(self, provider: Optional[CalendarProvider] = None):
        if provider is not None:
            self.provider = provider
            return

        from app.config import get_settings
        settings = get_settings()
        self.provider = GoogleCalendarProvider(
            refresh_token=settings.GOOGLE_CALENDAR_REFRESH_TOKEN,
            client_id=settings.GOOGLE_CALENDAR_CLIENT_ID,
            client_secret=settings.GOOGLE_CALENDAR_CLIENT_SECRET,
        )
        
    async def get_availability(self, calendar_id: str, start_time: datetime, end_time: datetime) -> List[TimeSlot]:
        """Get busy times."""
        return await self.provider.get_busy_slots(calendar_id, start_time, end_time)
        
    async def create_event(
        self,
        calendar_id: str,
        title: str,
        start_time: datetime,
        end_time: datetime,
        attendee_emails: List[str]
    ) -> CalendarEvent:
        """Create calendar event."""
        return await self.provider.create_event(
            calendar_id=calendar_id,
            title=title,
            start_time=start_time,
            end_time=end_time,
            attendee_emails=attendee_emails
        )
        
    async def cancel_event(self, calendar_id: str, event_id: str) -> bool:
        return await self.provider.cancel_event(calendar_id, event_id)
