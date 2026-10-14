"""Vertical slice coverage for the complete lead-to-draft pipeline."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api import leads as leads_api
from app.config import Settings
from app.database.base import Base
from app.models.agent_run import AgentRun
from app.models.campaign_lead import CampaignLead
from app.models.company_intelligence import CompanyIntelligence
from app.models.contact import Contact
from app.models.lead import Lead
from app.models.message import Message
from app.models.organization import Organization
from app.models.user import User
from app.schemas.hunter import (
    DiscoveredCompany,
    DiscoveredPerson,
    VerificationResult,
    VerificationStatus,
)
from app.schemas.personalization import GeneratedMessage
from app.schemas.website_intelligence import (
    ExtractedIntelligence,
    IntelligenceWithEvidence,
)
from app.services.discovery_service import DiscoveryService
from app.services.enrichment_service import EnrichmentService
from app.services.intent_service import IntentService
from app.services.personalization_service import PersonalizationService
from app.services.verification_service import VerificationService


@pytest.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as session:
        yield session
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.mark.asyncio
async def test_lead_pipeline_persists_verified_lead_intelligence_score_and_draft(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    org_id = uuid.uuid4()
    organization = Organization(
        id=org_id,
        name="Vertical Slice Org",
        slug=f"vertical-{org_id.hex[:8]}",
    )
    user = User(
        organization_id=org_id,
        email=f"{org_id.hex[:8]}@example.test",
        full_name="Pipeline Tester",
    )
    db_session.add_all([organization, user])
    await db_session.commit()

    company = DiscoveredCompany(
        name="Evidence Realty",
        domain="evidence-realty.example",
        website_url="https://evidence-realty.example",
        industry="Real Estate",
        country="US",
        source="mock",
    )
    person = DiscoveredPerson(
        first_name="Taylor",
        last_name="Prospect",
        job_title="CEO",
        email="taylor@evidence-realty.example",
        source="mock",
    )
    verification = VerificationResult(
        contact_value=person.email,
        status=VerificationStatus.valid,
        confidence=0.9,
        provider="mock_verification",
    )
    intelligence = IntelligenceWithEvidence(
        intelligence=ExtractedIntelligence(
            services=["Residential property management"],
            target_market=["Property owners"],
            locations=["US"],
            unique_selling_points=["Local operating team"],
        ),
        evidence={"services": ["https://evidence-realty.example/services"]},
        confidence=0.8,
        pages_analyzed=1,
        model_used="mock-llm",
    )

    class StubWebsiteGraph:
        async def ainvoke(self, _state):
            return {"extracted_intelligence": intelligence, "errors": []}

    monkeypatch.setattr(
        "app.config.get_settings",
        lambda: Settings(
            DISCOVERY_PROVIDER="mock",
            ENRICHMENT_PROVIDER="mock",
            VERIFICATION_PROVIDER="mock",
        ),
    )
    monkeypatch.setattr(DiscoveryService, "search", AsyncMock(return_value=[company]))
    monkeypatch.setattr(
        EnrichmentService,
        "find_people",
        AsyncMock(return_value=[person]),
    )
    monkeypatch.setattr(
        EnrichmentService,
        "enrich_company",
        AsyncMock(return_value=company),
    )
    monkeypatch.setattr(
        VerificationService,
        "verify_email",
        AsyncMock(return_value=verification),
    )
    monkeypatch.setattr(leads_api, "get_llm", lambda _settings=None: object())
    monkeypatch.setattr(
        "app.workflows.website_intelligence_workflow.build_website_intelligence_graph",
        lambda *_args: StubWebsiteGraph(),
    )
    monkeypatch.setattr(IntentService, "detect_intent", AsyncMock(return_value=[]))
    monkeypatch.setattr(
        PersonalizationService,
        "generate_message",
        AsyncMock(
            return_value=GeneratedMessage(
                subject="Property operations",
                opening="Hi Taylor, your local property management focus stood out.",
                value_proposition=(
                    "We help property teams coordinate qualified owner conversations "
                    "and improve their pipeline."
                ),
                cta="Would a short introduction next week be useful?",
            )
        ),
    )

    result = await leads_api.find_and_generate_leads(
        leads_api.LeadDiscoveryRequest(
            industry="Real Estate",
            country="US",
            max_companies=1,
        ),
        current_user=user,
        db=db_session,
    )

    assert result["status"] == "completed"
    assert result["lead_count"] == 1
    assert result["draft_count"] == 1
    assert all(
        result["steps"][step]["status"] == "succeeded"
        for step in (
            "discovery",
            "deduplication",
            "people_discovery",
            "enrichment",
            "verification",
            "persistence",
            "intelligence",
            "scoring",
            "draft_generation",
        )
    )

    lead = (await db_session.execute(select(Lead))).scalar_one()
    contact = (await db_session.execute(select(Contact))).scalar_one()
    company_intel = (
        await db_session.execute(select(CompanyIntelligence))
    ).scalar_one()
    campaign_link = (await db_session.execute(select(CampaignLead))).scalar_one()
    message = (await db_session.execute(select(Message))).scalar_one()
    run = (await db_session.execute(select(AgentRun))).scalar_one()

    assert contact.value == person.email
    assert contact.is_verified is True
    assert company_intel.services == ["Residential property management"]
    assert lead.score is not None
    assert campaign_link.lead_id == lead.id
    assert message.lead_id == lead.id
    assert message.status == "pending_approval"
    assert run.status == "completed"
    assert run.output_data["steps"]["draft_generation"]["draft_count"] == 1
