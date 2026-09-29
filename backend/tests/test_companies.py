import pytest
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.organization import Organization
from app.schemas.company import CompanyCreate, CompanyUpdate
from app.services.company_service import (
    create_company, get_company, get_company_by_domain,
    list_companies, update_company, delete_company
)

@pytest.fixture
async def setup_data(async_session: AsyncSession):
    org = Organization(name="Test Org", slug="test-org")
    async_session.add(org)
    await async_session.commit()
    await async_session.refresh(org)
    return org

@pytest.mark.asyncio
async def test_create_company(async_session: AsyncSession, setup_data):
    org = setup_data
    data = CompanyCreate(name="Test Co", organization_id=org.id, domain="testco.com")
    company = await create_company(async_session, data)
    assert company.id is not None
    assert company.name == "Test Co"
    assert company.organization_id == org.id

@pytest.mark.asyncio
async def test_get_company(async_session: AsyncSession, setup_data):
    org = setup_data
    data = CompanyCreate(name="Test Co 2", organization_id=org.id)
    company = await create_company(async_session, data)
    
    fetched = await get_company(async_session, company.id)
    assert fetched is not None
    assert fetched.id == company.id
    assert fetched.name == "Test Co 2"

@pytest.mark.asyncio
async def test_get_by_domain(async_session: AsyncSession, setup_data):
    org = setup_data
    data = CompanyCreate(name="Domain Co", organization_id=org.id, domain="domainco.com")
    await create_company(async_session, data)
    
    fetched = await get_company_by_domain(async_session, "domainco.com", org.id)
    assert fetched is not None
    assert fetched.domain == "domainco.com"

@pytest.mark.asyncio
async def test_list_companies(async_session: AsyncSession, setup_data):
    org = setup_data
    for i in range(3):
        await create_company(async_session, CompanyCreate(name=f"List Co {i}", organization_id=org.id))
    
    companies, total = await list_companies(async_session, org.id)
    assert total >= 3
    assert len(companies) >= 3

@pytest.mark.asyncio
async def test_update_company(async_session: AsyncSession, setup_data):
    org = setup_data
    data = CompanyCreate(name="Update Co", organization_id=org.id)
    company = await create_company(async_session, data)
    
    update_data = CompanyUpdate(name="Updated Co Name", employee_count=50)
    updated = await update_company(async_session, company.id, update_data)
    assert updated is not None
    assert updated.name == "Updated Co Name"
    assert updated.employee_count == 50

@pytest.mark.asyncio
async def test_delete_company(async_session: AsyncSession, setup_data):
    org = setup_data
    data = CompanyCreate(name="Delete Co", organization_id=org.id)
    company = await create_company(async_session, data)
    
    deleted = await delete_company(async_session, company.id)
    assert deleted is True
    
    fetched = await get_company(async_session, company.id)
    assert fetched is None
