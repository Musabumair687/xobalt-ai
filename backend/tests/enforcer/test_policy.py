"""Tests for Policy Engine."""

import pytest
import uuid
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.database.base import Base
from app.models.message import Message
from app.models.lead import Lead
from app.models.company import Company
from app.models.person import Person
from app.models.contact import Contact
from app.models.campaign import Campaign
from app.services.policy_service import PolicyService

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
async def test_policy_allow(db_session: AsyncSession):
    org_id = uuid.uuid4()
    campaign = Campaign(organization_id=org_id, name="Test Campaign", status="active", daily_limit=30)
    company = Company(organization_id=org_id, name="ABC")
    person = Person(organization_id=org_id, company=company, first_name="John", last_name="Doe")
    contact = Contact(person=person, type="email", value="john@test.com")
    db_session.add(campaign)
    db_session.add(company)
    db_session.add(person)
    db_session.add(contact)
    await db_session.flush()
    
    lead = Lead(organization_id=org_id, company_id=company.id, person_id=person.id)
    db_session.add(lead)
    await db_session.flush()
    
    msg = Message(organization_id=org_id, campaign_id=campaign.id, lead_id=lead.id, channel="email", direction="outbound", status="approved", body="Hello")
    db_session.add(msg)
    await db_session.commit()
    
    service = PolicyService(db_session)
    result = await service.evaluate(msg, lead, campaign)
    assert result.allowed is True
    assert len(result.reasons) == 0

@pytest.mark.asyncio
async def test_policy_block_unapproved(db_session: AsyncSession):
    org_id = uuid.uuid4()
    campaign = Campaign(organization_id=org_id, name="Test Campaign", status="active")
    company = Company(organization_id=org_id, name="ABC")
    person = Person(organization_id=org_id, company=company, first_name="John", last_name="Doe")
    contact = Contact(person=person, type="email", value="john@test.com")
    db_session.add(campaign)
    db_session.add(company)
    db_session.add(person)
    db_session.add(contact)
    await db_session.flush()
    
    lead = Lead(organization_id=org_id, company_id=company.id, person_id=person.id)
    db_session.add(lead)
    await db_session.flush()
    
    msg = Message(organization_id=org_id, campaign_id=campaign.id, lead_id=lead.id, channel="email", direction="outbound", status="pending_approval", body="Hello")
    db_session.add(msg)
    await db_session.commit()
    
    service = PolicyService(db_session)
    result = await service.evaluate(msg, lead, campaign)
    assert result.allowed is False
    assert any("must be 'approved'" in r for r in result.reasons)

@pytest.mark.asyncio
async def test_policy_block_opted_out(db_session: AsyncSession):
    org_id = uuid.uuid4()
    campaign = Campaign(organization_id=org_id, name="Test Campaign", status="active")
    company = Company(organization_id=org_id, name="ABC")
    person = Person(organization_id=org_id, company=company, first_name="John", last_name="Doe", metadata_={"opted_out": True})
    contact = Contact(person=person, type="email", value="john@test.com")
    db_session.add(campaign)
    db_session.add(company)
    db_session.add(person)
    db_session.add(contact)
    await db_session.flush()
    
    lead = Lead(organization_id=org_id, company_id=company.id, person_id=person.id)
    db_session.add(lead)
    await db_session.flush()
    
    msg = Message(organization_id=org_id, campaign_id=campaign.id, lead_id=lead.id, channel="email", direction="outbound", status="approved", body="Hello")
    db_session.add(msg)
    await db_session.commit()
    
    service = PolicyService(db_session)
    result = await service.evaluate(msg, lead, campaign)
    assert result.allowed is False
    assert any("opted out" in r for r in result.reasons)
