"""Tests for the complete Scoring/Intent LangGraph Workflow."""

import pytest
import uuid
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.database.base import Base
import app.models # ensure all registered
from app.models.organization import Organization
from app.models.company import Company
from app.models.person import Person
from app.models.lead import Lead
from app.workflows.scoring_intent_workflow import build_scoring_intent_graph

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
async def test_scoring_workflow_end_to_end(db_session: AsyncSession):
    # Setup Data
    org_id = uuid.uuid4()
    org = Organization(id=org_id, name="Test Org", slug="test-org")
    db_session.add(org)
    
    company = Company(name="Test Company", organization_id=org_id, industry="Real Estate", employee_count=45, state="Texas")
    person = Person(organization_id=org_id, company=company, first_name="John", last_name="Doe", title="CEO")
    db_session.add(company)
    db_session.add(person)
    await db_session.flush()
    
    lead = Lead(organization_id=org_id, company_id=company.id, person_id=person.id)
    db_session.add(lead)
    await db_session.commit()
    
    # We patch the services so we don't need real LLMs
    mock_intent_signals = [
        {"signal_type": "HIRING", "description": "test", "evidence": "test", "confidence": 0.9}
    ]
    
    with patch(
        "app.services.intent_service.IntentService.detect_intent",
        new_callable=AsyncMock,
        return_value=mock_intent_signals
    ):
        from app.services.intent_service import IntentService
        from app.services.intent_signal_service import IntentSignalService
        from app.services.scoring_service import ScoringService
        
        intent_svc = IntentService(AsyncMock())
        signal_svc = IntentSignalService(db_session)
        score_svc = ScoringService()
        
        graph = build_scoring_intent_graph(db_session, intent_svc, signal_svc, score_svc)
        
        final_state = await graph.ainvoke({"lead_id": lead.id, "errors": []})
        
    assert "errors" not in final_state or not final_state["errors"]
    assert final_state["total_score"] > 0
    
    # DB Should be updated
    await db_session.refresh(lead)
    assert lead.score == final_state["total_score"]
    assert lead.qualification_status == final_state["classification"].lower()
    
    # Check breakdown saved
    assert "score_breakdown" in lead.metadata_
    assert lead.metadata_["score_breakdown"]["industry_match"]["score"] == 25
