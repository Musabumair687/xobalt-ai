"""End-to-end workflow test for the Hunter LangGraph graph.

These tests run the FULL workflow graph (discover → deduplicate →
find_people → enrich → verify → store) using mock providers and a
real in-memory SQLite database — no live API calls needed.

The goal: validate that state is passed correctly between every node and
that the `store` node actually writes Lead rows to the DB.
"""

from __future__ import annotations

import uuid
import pytest
from unittest.mock import AsyncMock, patch

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

import app.models  # ensure all models are registered
from app.database.base import Base
from app.schemas.hunter import (
    DiscoveredCompany,
    DiscoveredPerson,
    HunterCriteria,
    VerificationResult,
    VerificationStatus,
)
from app.workflows.hunter_workflow import build_hunter_graph, get_initial_state


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def db_session():
    """Provide an isolated in-memory SQLite session per test."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


def _criteria(org_id: uuid.UUID) -> HunterCriteria:
    return HunterCriteria(
        organization_id=org_id,
        industry="Real Estate",
        country="US",
        min_employees=10,
        max_employees=100,
        decision_maker_roles=["CEO", "Founder"],
        max_companies=5,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_workflow_runs_without_db():
    """The graph should complete (with a warning) even when db=None."""
    criteria = _criteria(uuid.uuid4())
    initial = get_initial_state(criteria.model_dump())

    graph = build_hunter_graph(db=None)
    final = await graph.ainvoke(initial)

    assert isinstance(final["lead_ids"], list)
    assert "no_db_session" in final.get("warnings", [])


@pytest.mark.asyncio
async def test_workflow_deduplication_stage():
    """Duplicate companies in discovery output are collapsed before find_people.

    We patch DiscoveryService.search so the discover_companies node returns
    3 companies (2 with the same domain). The dedup node must collapse them to 2.
    """
    org_id = uuid.uuid4()
    companies = [
        DiscoveredCompany(name="ABC Realty", domain="https://www.abc-realty.com/"),
        DiscoveredCompany(name="ABC Realty LLC", domain="abc-realty.com"),
        DiscoveredCompany(name="XYZ Properties", domain="xyz.com"),
    ]

    with patch(
        "app.services.discovery_service.DiscoveryService.search",
        new_callable=AsyncMock,
        return_value=companies,
    ):
        criteria = _criteria(org_id)
        initial = get_initial_state(criteria.model_dump())
        graph = build_hunter_graph(db=None)
        final = await graph.ainvoke(initial)

    # 2 unique domains: abc-realty.com, xyz.com
    assert len(final["deduplicated_companies"]) == 2


@pytest.mark.asyncio
async def test_workflow_stores_leads(db_session: AsyncSession):
    """Full workflow with mocked discovery/enrichment → real DB store → Lead created."""
    from sqlalchemy import select
    from app.models.lead import Lead
    from app.models.organization import Organization

    # Seed an organization row
    org_id = uuid.uuid4()
    org = Organization(id=org_id, name="Test Org", slug=f"test-org-{org_id.hex[:6]}")
    db_session.add(org)
    await db_session.commit()

    company = DiscoveredCompany(name="ABC Realty", domain="abc-realty.com", source="test")
    person = DiscoveredPerson(
        first_name="John",
        last_name="Smith",
        job_title="CEO",
        email="john@abc-realty.com",
        source="test",
    )

    with (
        patch(
            "app.services.discovery_service.DiscoveryService.search",
            new_callable=AsyncMock,
            return_value=[company],
        ),
        patch(
            "app.services.enrichment_service.EnrichmentService.enrich_company",
            new_callable=AsyncMock,
            return_value=company,
        ),
        patch(
            "app.services.enrichment_service.EnrichmentService.find_people",
            new_callable=AsyncMock,
            return_value=[person],
        ),
    ):
        criteria = _criteria(org_id)
        initial = get_initial_state(criteria.model_dump())
        graph = build_hunter_graph(db=db_session)
        final = await graph.ainvoke(initial)

    assert len(final["lead_ids"]) == 1

    # Verify the lead is in the DB
    result = await db_session.execute(select(Lead).where(Lead.organization_id == org_id))
    leads = result.scalars().all()
    assert len(leads) == 1
    assert leads[0].status == "new"


@pytest.mark.asyncio
async def test_workflow_error_tolerance():
    """A failing discovery source should not crash the entire workflow."""
    with patch(
        "app.services.discovery_service.DiscoveryService.search",
        new_callable=AsyncMock,
        side_effect=RuntimeError("Provider down"),
    ):
        criteria = _criteria(uuid.uuid4())
        initial = get_initial_state(criteria.model_dump())
        graph = build_hunter_graph(db=None)
        final = await graph.ainvoke(initial)

    # Errors are captured, workflow still finishes
    assert any("discovery_error" in e for e in final.get("errors", []))
    assert isinstance(final["lead_ids"], list)
