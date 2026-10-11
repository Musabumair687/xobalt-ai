"""Tests for Booking Service."""

import pytest
import uuid
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.database.base import Base
from app.models.organization import Organization
from app.models.company import Company
from app.models.person import Person
from app.models.contact import Contact
from app.models.lead import Lead
from app.models.conversation import Conversation
from app.services.calendar_service import CalendarService
from app.services.availability_service import AvailabilityService
from app.services.appointment_service import AppointmentService
from app.services.booking_service import BookingService
from app.schemas.calendar import BookingRequest, TimeSlot, CalendarEvent

@pytest.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest.fixture
async def setup_data(db_session: AsyncSession):
    org_id = uuid.uuid4()
    org = Organization(id=org_id, name="Test Org", slug="test-org")
    company = Company(name="Test Company", organization_id=org_id, industry="Real Estate")
    person = Person(organization_id=org_id, company=company, first_name="John", last_name="Doe")
    contact = Contact(person=person, type="email", value="john@test.com")
    db_session.add_all([org, company, person, contact])
    await db_session.flush()
    
    lead = Lead(organization_id=org_id, company_id=company.id, person_id=person.id)
    db_session.add(lead)
    await db_session.flush()
    
    conv = Conversation(organization_id=org_id, lead_id=lead.id, status="active")
    db_session.add(conv)
    await db_session.commit()
    return {"org_id": org_id, "lead_id": lead.id, "conv_id": conv.id}

@pytest.mark.asyncio
async def test_booking_success(db_session: AsyncSession, setup_data):
    cal_svc = CalendarService()
    cal_svc.get_availability = AsyncMock(return_value=[])  # Calendar is free
    cal_svc.create_event = AsyncMock(return_value=CalendarEvent(
        id="evt_123", title="Test", start_time=datetime.now(), end_time=datetime.now(), status="confirmed"
    ))
    
    avail_svc = AvailabilityService()
    appt_svc = AppointmentService(db_session)
    booking_svc = BookingService(cal_svc, avail_svc, appt_svc)
    
    req = BookingRequest(
        slot=TimeSlot(start_time=datetime(2026,10,8,9,0), end_time=datetime(2026,10,8,10,0)),
        lead_id=str(setup_data["lead_id"]),
        calendar_id="cal_123",
        organization_id=str(setup_data["org_id"])
    )
    
    result = await booking_svc.book_meeting(req, setup_data["conv_id"], "Test Title", ["john@test.com"])
    
    assert result.success is True
    assert result.event_id == "evt_123"
    assert result.appointment_id is not None

@pytest.mark.asyncio
async def test_booking_failure_double_booked(db_session: AsyncSession, setup_data):
    cal_svc = CalendarService()
    # Calendar says this exact slot is busy
    cal_svc.get_availability = AsyncMock(return_value=[
        TimeSlot(start_time=datetime(2026,10,8,9,0), end_time=datetime(2026,10,8,10,0))
    ])
    
    avail_svc = AvailabilityService()
    appt_svc = AppointmentService(db_session)
    booking_svc = BookingService(cal_svc, avail_svc, appt_svc)
    
    req = BookingRequest(
        slot=TimeSlot(start_time=datetime(2026,10,8,9,0), end_time=datetime(2026,10,8,10,0)),
        lead_id=str(setup_data["lead_id"]),
        calendar_id="cal_123",
        organization_id=str(setup_data["org_id"])
    )
    
    result = await booking_svc.book_meeting(req, setup_data["conv_id"], "Test Title", ["john@test.com"])
    
    assert result.success is False
    assert "no longer available" in result.error
