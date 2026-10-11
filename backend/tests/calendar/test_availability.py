"""Tests for Availability Service."""

import pytest
from datetime import datetime, timezone, timedelta
from app.services.availability_service import AvailabilityService
from app.schemas.calendar import AvailabilityRequest, TimeSlot

def test_generate_candidates():
    svc = AvailabilityService(work_start_hour=9, work_end_hour=11)
    req = AvailabilityRequest(
        start_date=datetime(2026, 10, 8, 0, 0, tzinfo=timezone.utc),
        end_date=datetime(2026, 10, 8, 12, 0, tzinfo=timezone.utc),
        duration_minutes=60,
        timezone="UTC"
    )
    
    slots = svc.generate_candidate_slots(req)
    # Should only generate slots within 9-11: (9-10) and (10-11)
    assert len(slots) == 2
    assert slots[0].start_time.hour == 9
    assert slots[1].start_time.hour == 10

def test_find_available():
    svc = AvailabilityService()
    cands = [
        TimeSlot(start_time=datetime(2026,10,8,9,0), end_time=datetime(2026,10,8,10,0)),
        TimeSlot(start_time=datetime(2026,10,8,10,0), end_time=datetime(2026,10,8,11,0))
    ]
    busy = [
        TimeSlot(start_time=datetime(2026,10,8,9,30), end_time=datetime(2026,10,8,10,30))
    ]
    
    available = svc.find_available_slots(cands, busy)
    # Both candidates overlap with 9:30-10:30
    assert len(available) == 0
    
    busy2 = [
        TimeSlot(start_time=datetime(2026,10,8,10,0), end_time=datetime(2026,10,8,11,0))
    ]
    available2 = svc.find_available_slots(cands, busy2)
    # 9-10 is free, 10-11 is busy
    assert len(available2) == 1
    assert available2[0].start_time.hour == 9
