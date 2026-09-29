import pytest
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.organization import Organization
from app.models.company import Company
from app.models.person import Person
from app.schemas.lead import LeadCreate, LeadUpdate, LeadStatusEnum
from app.services.lead_service import (
    create_lead, get_lead, list_leads, update_lead,
    update_lead_score, update_lead_status, delete_lead
)

@pytest.fixture
async def setup_data(async_session: AsyncSession):
    org = Organization(name="Lead Org", slug="lead-org")
    async_session.add(org)
    await async_session.commit()
    await async_session.refresh(org)
    
    company = Company(name="Lead Co", organization_id=org.id)
    async_session.add(company)
    await async_session.commit()
    await async_session.refresh(company)
    
    person = Person(first_name="John", last_name="Doe", organization_id=org.id, company_id=company.id)
    async_session.add(person)
    await async_session.commit()
    await async_session.refresh(person)
    
    return org, company, person

@pytest.mark.asyncio
async def test_create_lead(async_session: AsyncSession, setup_data):
    org, company, person = setup_data
    data = LeadCreate(organization_id=org.id, person_id=person.id, company_id=company.id, score=50)
    lead = await create_lead(async_session, data)
    assert lead.id is not None
    assert lead.organization_id == org.id
    assert lead.person_id == person.id
    assert lead.score == 50

@pytest.mark.asyncio
async def test_get_lead(async_session: AsyncSession, setup_data):
    org, _, _ = setup_data
    data = LeadCreate(organization_id=org.id)
    lead = await create_lead(async_session, data)
    
    fetched = await get_lead(async_session, lead.id)
    assert fetched is not None
    assert fetched.id == lead.id

@pytest.mark.asyncio
async def test_list_leads(async_session: AsyncSession, setup_data):
    org, _, _ = setup_data
    await create_lead(async_session, LeadCreate(organization_id=org.id, status=LeadStatusEnum.new))
    await create_lead(async_session, LeadCreate(organization_id=org.id, status=LeadStatusEnum.contacted))
    
    leads, total = await list_leads(async_session, org.id)
    assert total >= 2
    
    leads_new, total_new = await list_leads(async_session, org.id, status=LeadStatusEnum.new)
    assert total_new >= 1

@pytest.mark.asyncio
async def test_update_status(async_session: AsyncSession, setup_data):
    org, _, _ = setup_data
    lead = await create_lead(async_session, LeadCreate(organization_id=org.id))
    
    updated = await update_lead_status(async_session, lead.id, LeadStatusEnum.qualified)
    assert updated.status == LeadStatusEnum.qualified

@pytest.mark.asyncio
async def test_update_score(async_session: AsyncSession, setup_data):
    org, _, _ = setup_data
    lead = await create_lead(async_session, LeadCreate(organization_id=org.id))
    
    updated = await update_lead_score(async_session, lead.id, 85)
    assert updated.score == 85

@pytest.mark.asyncio
async def test_delete_lead(async_session: AsyncSession, setup_data):
    org, _, _ = setup_data
    lead = await create_lead(async_session, LeadCreate(organization_id=org.id))
    
    deleted = await delete_lead(async_session, lead.id)
    assert deleted is True
    
    fetched = await get_lead(async_session, lead.id)
    assert fetched is None
