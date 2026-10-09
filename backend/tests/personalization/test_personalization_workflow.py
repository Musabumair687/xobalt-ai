"""Tests for Personalization LangGraph Workflow."""

import pytest
import uuid
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.database.base import Base
from app.models.organization import Organization
from app.models.company import Company
from app.models.person import Person
from app.models.lead import Lead
from app.models.campaign import Campaign
from app.models.message import Message
from app.schemas.personalization import GeneratedMessage
from app.workflows.personalization_workflow import build_personalization_graph
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
async def test_personalization_workflow_end_to_end(db_session: AsyncSession):
    # Setup Data
    org_id = uuid.uuid4()
    org = Organization(id=org_id, name="Test Org", slug="test-org")
    db_session.add(org)
    
    company = Company(name="Test Company", organization_id=org_id, industry="Real Estate")
    person = Person(organization_id=org_id, company=company, first_name="John", last_name="Doe")
    campaign = Campaign(organization_id=org_id, name="Test Campaign")
    db_session.add(company)
    db_session.add(person)
    db_session.add(campaign)
    await db_session.flush()
    
    lead = Lead(organization_id=org_id, company_id=company.id, person_id=person.id)
    db_session.add(lead)
    await db_session.commit()
    
    # Mock LLM Output
    mock_msg = GeneratedMessage(
        subject="Test Subject",
        opening="Test Opening",
        value_proposition="Test Value Proposition that is long enough.",
        cta="Test CTA"
    )
    
    with patch(
        "app.services.personalization_service.PersonalizationService.generate_message",
        new_callable=AsyncMock,
        return_value=mock_msg
    ):
        from app.services.personalization_service import PersonalizationService
        from app.services.message_validation_service import MessageValidationService
        
        p_svc = PersonalizationService(AsyncMock())
        v_svc = MessageValidationService()
        
        graph = build_personalization_graph(db_session, p_svc, v_svc)
        
        final_state = await graph.ainvoke({
            "lead_id": lead.id, 
            "campaign_id": campaign.id,
            "errors": [],
            "warnings": []
        })
        
    assert "errors" not in final_state or not final_state["errors"]
    assert final_state["approval_status"] == "pending_approval"
    
    # Check that message was created in DB
    msg_id = final_state["message_id"]
    res = await db_session.execute(select(Message).where(Message.id == msg_id))
    msg = res.scalars().first()
    
    assert msg is not None
    assert msg.subject == "Test Subject"
    assert "Test Value Proposition that is long enough." in msg.body
    assert msg.status == "pending_approval"
