"""Tests for Closer LangGraph Workflow."""

import pytest
import uuid
from unittest.mock import AsyncMock
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.database.base import Base
from app.models.organization import Organization
from app.models.company import Company
from app.models.person import Person
from app.models.contact import Contact
from app.models.lead import Lead
from app.models.campaign import Campaign
from app.models.campaign_lead import CampaignLead
from app.models.conversation import Conversation
from app.models.conversation_message import ConversationMessage
from app.workflows.closer_workflow import build_closer_graph
from app.services.conversation_context_service import ConversationContextService
from app.services.reply_classification_service import ReplyClassificationService
from app.services.response_service import ResponseService
from app.schemas.closer import ReplyClassification

class MockClassLLM:
    def __init__(self, intent, conf=0.9):
        self.intent = intent
        self.conf = conf
    def with_structured_output(self, schema): return self
    async def ainvoke(self, prompt): return ReplyClassification(intent=self.intent, confidence=self.conf, reason="t")

class MockRespLLM:
    async def ainvoke(self, args): return "Mock Response"

class MockResponseService(ResponseService):
    def __init__(self): pass
    async def generate_response(self, context_str: str, intent: str):
        return "Mock Response"

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
    campaign = Campaign(organization_id=org_id, name="Test Campaign", status="active")
    db_session.add_all([org, company, person, contact, campaign])
    await db_session.flush()
    
    lead = Lead(organization_id=org_id, company_id=company.id, person_id=person.id)
    db_session.add(lead)
    await db_session.flush()
    
    cl = CampaignLead(campaign_id=campaign.id, lead_id=lead.id)
    conv = Conversation(organization_id=org_id, lead_id=lead.id, status="active")
    db_session.add_all([cl, conv])
    await db_session.flush()
    
    msg = ConversationMessage(conversation_id=conv.id, direction="INBOUND", content="test", sequence_number=1)
    db_session.add(msg)
    await db_session.commit()
    return msg

@pytest.mark.asyncio
async def test_closer_workflow_question(db_session: AsyncSession, setup_data):
    msg = setup_data
    
    context_svc = ConversationContextService()
    class_svc = ReplyClassificationService(MockClassLLM("QUESTION"))
    resp_svc = MockResponseService()
    
    graph = build_closer_graph(db_session, context_svc, class_svc, resp_svc)
    final_state = await graph.ainvoke({"conversation_message_id": msg.id, "errors": []})
    
    assert final_state["action_taken"] == "GENERATED_RESPONSE_PENDING_APPROVAL"
    assert final_state["response_generated"] is True
    assert final_state["draft_response"] == "Mock Response"

@pytest.mark.asyncio
async def test_closer_workflow_interested(db_session: AsyncSession, setup_data):
    msg = setup_data
    
    context_svc = ConversationContextService()
    class_svc = ReplyClassificationService(MockClassLLM("INTERESTED"))
    resp_svc = MockResponseService()
    
    graph = build_closer_graph(db_session, context_svc, class_svc, resp_svc)
    final_state = await graph.ainvoke({"conversation_message_id": msg.id, "errors": []})
    
    assert final_state["action_taken"] == "ROUTED_TO_BOOKING"
    await db_session.refresh(msg.conversation)
    assert msg.conversation.status == "BOOKING"

@pytest.mark.asyncio
async def test_closer_workflow_unsubscribe(db_session: AsyncSession, setup_data):
    msg = setup_data
    
    context_svc = ConversationContextService()
    class_svc = ReplyClassificationService(MockClassLLM("UNSUBSCRIBE"))
    resp_svc = MockResponseService()
    
    graph = build_closer_graph(db_session, context_svc, class_svc, resp_svc)
    final_state = await graph.ainvoke({"conversation_message_id": msg.id, "errors": []})
    
    assert final_state["action_taken"] == "OPTED_OUT"
    await db_session.refresh(msg.conversation)
    assert msg.conversation.status == "OPTED_OUT"
