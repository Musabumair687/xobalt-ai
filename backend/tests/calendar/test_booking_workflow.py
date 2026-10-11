"""Tests for Booking LangGraph Workflow."""

import pytest
import uuid
from unittest.mock import AsyncMock
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.database.base import Base
from app.models.organization import Organization
from app.models.company import Company
from app.models.person import Person
from app.models.contact import Contact
from app.models.lead import Lead
from app.models.conversation import Conversation
from app.schemas.calendar import AvailabilityRequest, BookingRequest, TimeSlot, BookingResult
from app.workflows.booking_workflow import build_booking_graph

class MockBookingService:
    async def get_available_slots(self, req, cal_id):
        return [TimeSlot(start_time=datetime.now(), end_time=datetime.now())]
        
    async def book_meeting(self, request, conv_id, title, attendees):
        return BookingResult(success=True, event_id="mock_evt", appointment_id=str(uuid.uuid4()))

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

@pytest.mark.asyncio
async def test_booking_workflow_availability(db_session: AsyncSession):
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
    
    booking_svc = MockBookingService()
    graph = build_booking_graph(db_session, booking_svc)
    
    req = AvailabilityRequest(start_date=datetime.now(), end_date=datetime.now())
    state = {
        "conversation_id": conv.id,
        "action": "get_availability",
        "availability_request": req,
        "errors": []
    }
    
    final_state = await graph.ainvoke(state)
    assert len(final_state["available_slots"]) == 1

@pytest.mark.asyncio
async def test_booking_workflow_book(db_session: AsyncSession):
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
    
    booking_svc = MockBookingService()
    graph = build_booking_graph(db_session, booking_svc)
    
    req = BookingRequest(
        slot=TimeSlot(start_time=datetime.now(), end_time=datetime.now()),
        lead_id=str(lead.id),
        calendar_id="test",
        organization_id=str(org_id)
    )
    state = {
        "conversation_id": conv.id,
        "action": "book_slot",
        "booking_request": req,
        "errors": []
    }
    
    final_state = await graph.ainvoke(state)
    assert final_state["booking_result"].success is True
    
    await db_session.refresh(conv)
    assert conv.status == "BOOKED"
