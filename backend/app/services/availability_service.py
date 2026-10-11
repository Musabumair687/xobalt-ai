"""Service for computing available slots based on busy times and rules."""

import logging
from datetime import datetime, timedelta
from typing import List
from app.schemas.calendar import TimeSlot, AvailabilityRequest

logger = logging.getLogger(__name__)

class AvailabilityService:
    def __init__(self, work_start_hour: int = 9, work_end_hour: int = 17):
        """Simple setup with basic working hours (UTC)."""
        self.work_start_hour = work_start_hour
        self.work_end_hour = work_end_hour
        
    def generate_candidate_slots(self, request: AvailabilityRequest) -> List[TimeSlot]:
        """Generate all possible slots across the requested dates in the given duration."""
        slots = []
        current = request.start_date
        while current + timedelta(minutes=request.duration_minutes) <= request.end_date:
            if self.work_start_hour <= current.hour < self.work_end_hour:
                slots.append(TimeSlot(
                    start_time=current,
                    end_time=current + timedelta(minutes=request.duration_minutes),
                    timezone=request.timezone
                ))
            current += timedelta(minutes=request.duration_minutes)
        return slots
        
    def find_available_slots(self, candidates: List[TimeSlot], busy_slots: List[TimeSlot]) -> List[TimeSlot]:
        """Filter out candidates that overlap with busy slots."""
        available = []
        for cand in candidates:
            is_busy = False
            for b in busy_slots:
                # Overlap check
                if max(cand.start_time, b.start_time) < min(cand.end_time, b.end_time):
                    is_busy = True
                    break
            if not is_busy:
                available.append(cand)
        return available
