"""Tests for Inbox Worker."""

import pytest
import uuid
from unittest.mock import patch, AsyncMock
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.database.base import Base
from app.models.organization import Organization
from app.models.company import Company
from app.models.person import Person
from app.models.contact import Contact
from app.models.lead import Lead
from app.workers.inbox_worker import InboxWorker
from app.schemas.closer import ReplyClassification

class MockChatGroq:
    def __init__(self, *args, **kwargs):
        pass
    def with_structured_output(self, schema):
        return self
    async def ainvoke(self, prompt):
        if hasattr(prompt, 'messages') or isinstance(prompt, dict):
            # Response Service path
            return "Mock Response"
        # Classification path
        return ReplyClassification(intent="QUESTION", confidence=0.9, reason="test")

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
async def test_inbox_worker_process(db_session: AsyncSession):
    # Setup Data
    org_id = uuid.uuid4()
    org = Organization(id=org_id, name="Test Org", slug="test-org")
    company = Company(name="Test Company", organization_id=org_id, industry="Real Estate")
    person = Person(organization_id=org_id, company=company, first_name="John", last_name="Doe")
    contact = Contact(person=person, type="email", value="john@test.com")
    db_session.add_all([org, company, person, contact])
    await db_session.flush()
    
    lead = Lead(organization_id=org_id, company_id=company.id, person_id=person.id)
    db_session.add(lead)
    await db_session.commit()
    
    worker = InboxWorker(db_session)
    
    with patch("app.workers.inbox_worker.ChatGroq", new=MockChatGroq), \
         patch("app.services.response_service.ResponseService.generate_response", new_callable=AsyncMock) as mock_resp:
        mock_resp.return_value = "Mock Response"
        result = await worker.process_new_reply(
            "john@test.com",
            "Subject",
            "Hello",
            org_id,
        )
        
    assert result["action_taken"] == "GENERATED_RESPONSE_PENDING_APPROVAL"
