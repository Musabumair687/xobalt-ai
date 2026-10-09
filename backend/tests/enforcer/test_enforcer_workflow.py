"""Tests for Enforcer LangGraph Workflow."""

import pytest
import uuid
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.database.base import Base
from app.models.organization import Organization
from app.models.company import Company
from app.models.person import Person
from app.models.contact import Contact
from app.models.lead import Lead
from app.models.campaign import Campaign
from app.models.campaign_lead import CampaignLead
from app.models.message import Message
from app.models.message_event import MessageEvent
from app.workflows.enforcer_workflow import build_enforcer_graph
from sqlalchemy import select

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
async def test_enforcer_workflow_success(db_session: AsyncSession):
    # Setup Data
    org_id = uuid.uuid4()
    org = Organization(id=org_id, name="Test Org", slug="test-org")
    db_session.add(org)
    
    company = Company(name="Test Company", organization_id=org_id, industry="Real Estate")
    person = Person(organization_id=org_id, company=company, first_name="John", last_name="Doe")
    contact = Contact(person=person, type="email", value="john@test.com", is_primary=True)
    campaign = Campaign(organization_id=org_id, name="Test Campaign", status="active")
    db_session.add(company)
    db_session.add(person)
    db_session.add(contact)
    db_session.add(campaign)
    await db_session.flush()
    
    lead = Lead(organization_id=org_id, company_id=company.id, person_id=person.id)
    db_session.add(lead)
    await db_session.flush()
    
    cl = CampaignLead(campaign_id=campaign.id, lead_id=lead.id)
    db_session.add(cl)
    
    msg = Message(organization_id=org_id, campaign_id=campaign.id, lead_id=lead.id, channel="email", direction="outbound", status="approved", subject="Test", body="Test")
    db_session.add(msg)
    await db_session.commit()
    
    # Initialize Services
    from app.services.policy_service import PolicyService
    from app.services.outreach_service import OutreachService
    from app.services.message_event_service import MessageEventService
    from app.services.followup_service import FollowupService
    from app.integrations.email.base import EmailProvider
    
    class TestEmailProvider(EmailProvider):
        async def send_email(self, to_email, subject, body, from_email=None):
            return "ext-123"
            
    policy_svc = PolicyService(db_session)
    outreach_svc = OutreachService(db_session, TestEmailProvider())
    event_svc = MessageEventService(db_session)
    followup_svc = FollowupService(db_session)
    
    graph = build_enforcer_graph(db_session, policy_svc, outreach_svc, event_svc, followup_svc)
    
    final_state = await graph.ainvoke({"message_id": msg.id, "errors": []})
    
    assert final_state["status"] == "sent"
    assert final_state["event_recorded"] is True
    assert final_state["followup_scheduled"] is True
    
    # Verify DB updates
    await db_session.refresh(msg)
    assert msg.status == "sent"
    assert msg.external_id == "ext-123"
    
    res_ev = await db_session.execute(select(MessageEvent).where(MessageEvent.message_id == msg.id))
    event = res_ev.scalars().first()
    assert event is not None
    assert event.event_type == "MESSAGE_SENT"

@pytest.mark.asyncio
async def test_enforcer_workflow_blocked(db_session: AsyncSession):
    # Setup Data - Message not approved
    org_id = uuid.uuid4()
    company = Company(name="Test Company", organization_id=org_id, industry="Real Estate")
    person = Person(organization_id=org_id, company=company, first_name="John", last_name="Doe")
    contact = Contact(person=person, type="email", value="john@test.com")
    campaign = Campaign(organization_id=org_id, name="Test Campaign", status="active")
    db_session.add_all([company, person, contact, campaign])
    await db_session.flush()
    
    lead = Lead(organization_id=org_id, company_id=company.id, person_id=person.id)
    db_session.add(lead)
    await db_session.flush()
    
    msg = Message(organization_id=org_id, campaign_id=campaign.id, lead_id=lead.id, channel="email", direction="outbound", status="draft", subject="Test", body="Test")
    db_session.add(msg)
    await db_session.commit()
    
    # Initialize Services
    from app.services.policy_service import PolicyService
    from app.services.outreach_service import OutreachService
    from app.services.message_event_service import MessageEventService
    from app.services.followup_service import FollowupService
    from app.integrations.email.gmail import GmailProvider
    
    policy_svc = PolicyService(db_session)
    outreach_svc = OutreachService(db_session, GmailProvider())
    event_svc = MessageEventService(db_session)
    followup_svc = FollowupService(db_session)
    
    graph = build_enforcer_graph(db_session, policy_svc, outreach_svc, event_svc, followup_svc)
    
    final_state = await graph.ainvoke({"message_id": msg.id, "errors": []})
    
    assert final_state["status"] == "blocked"
    assert final_state["event_recorded"] is True
    assert final_state.get("followup_scheduled") is not True
    
    # Check that block event was recorded
    res_ev = await db_session.execute(select(MessageEvent).where(MessageEvent.message_id == msg.id))
    event = res_ev.scalars().first()
    assert event is not None
    assert event.event_type == "MESSAGE_BLOCKED"
    assert "must be 'approved'" in event.event_data["reasons"][0]
