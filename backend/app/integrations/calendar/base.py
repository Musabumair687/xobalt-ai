"""Base interface for Calendar integrations."""

from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime
from app.schemas.calendar import TimeSlot, CalendarEvent

class CalendarProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass
        
    @abstractmethod
    async def get_busy_slots(self, calendar_id: str, start_time: datetime, end_time: datetime) -> List[TimeSlot]:
        """Fetch busy periods from the provider."""
        pass
        
    @abstractmethod
    async def create_event(
        self,
        calendar_id: str,
        title: str,
        start_time: datetime,
        end_time: datetime,
        attendee_emails: List[str],
        description: Optional[str] = None
    ) -> CalendarEvent:
        """Create a new event."""
        pass
        
    @abstractmethod
    async def cancel_event(self, calendar_id: str, event_id: str) -> bool:
        """Cancel an event."""
        pass
