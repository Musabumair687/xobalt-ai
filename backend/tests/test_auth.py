import uuid
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import hash_password
from app.config import get_settings
from app.database.dependencies import get_db
from app.main import app
from app.models.campaign import Campaign
from app.models.agent_run import AgentRun
from app.models.company import Company
from app.models.contact import Contact
from app.models.lead import Lead
from app.models.message import Message
from app.models.organization import Organization
from app.models.person import Person
from app.models.user import User


@pytest.fixture
def jwt_secret(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "phase-four-test-secret-" + "x" * 32)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_login_and_organization_access_are_enforced(
    async_session: AsyncSession,
    jwt_secret,
):
    org_a = Organization(name="Org A", slug=f"org-a-{uuid.uuid4().hex}")
    org_b = Organization(name="Org B", slug=f"org-b-{uuid.uuid4().hex}")
    async_session.add_all([org_a, org_b])
    await async_session.flush()

    password = "long-test-password-123"
    user_a = User(
        organization_id=org_a.id,
        email=f"{uuid.uuid4().hex}@example.com",
        full_name="Org A Owner",
        role="owner",
        hashed_password=hash_password(password),
    )
    async_session.add(user_a)
    company_a = Company(
        organization_id=org_a.id,
        name="Company A",
    )
    company_b = Company(
        organization_id=org_b.id,
        name="Company B",
    )
    async_session.add_all([company_a, company_b])
    await async_session.flush()
    own_campaign = Campaign(organization_id=org_a.id, name="Own campaign")
    foreign_campaign = Campaign(organization_id=org_b.id, name="Foreign campaign")
    person_a = Person(
        organization_id=org_a.id,
        company_id=company_a.id,
        first_name="Test",
        last_name="Recipient",
    )
    async_session.add_all([own_campaign, foreign_campaign, person_a])
    await async_session.flush()
    contact_a = Contact(
        person_id=person_a.id,
        type="email",
        value="recipient@example.com",
    )
    lead_a = Lead(
        organization_id=org_a.id,
        company_id=company_a.id,
        person_id=person_a.id,
    )
    async_session.add_all([contact_a, lead_a])
    await async_session.flush()
    own_approved_message = Message(
        organization_id=org_a.id,
        campaign_id=own_campaign.id,
        lead_id=lead_a.id,
        channel="email",
        direction="outbound",
        subject="Approved",
        body="Approved message",
        status="approved",
    )
    own_pending_message = Message(
        organization_id=org_a.id,
        campaign_id=own_campaign.id,
        lead_id=lead_a.id,
        channel="email",
        direction="outbound",
        subject="Pending",
        body="Pending message",
        status="pending_approval",
    )
    await async_session.flush()
    foreign_message = Message(
        organization_id=org_b.id,
        campaign_id=foreign_campaign.id,
        channel="email",
        direction="outbound",
        subject="Private",
        body="Private",
        status="approved",
    )
    async_session.add_all([own_approved_message, own_pending_message, foreign_message])
    await async_session.commit()

    async def override_get_db():
        yield async_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            assert (await client.get("/health")).status_code == 200
            unauthenticated = await client.get("/api/v1/companies")
            assert unauthenticated.status_code == 401

            login = await client.post(
                "/api/v1/auth/login",
                json={"email": user_a.email, "password": password},
            )
            assert login.status_code == 200
            token = login.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}

            companies = await client.get(
                "/api/v1/companies?page=1&page_size=1&query=Company",
                headers=headers,
            )
            assert companies.status_code == 200
            companies_page = companies.json()
            assert [company["id"] for company in companies_page["items"]] == [str(company_a.id)]
            assert companies_page["page"] == 1
            assert companies_page["page_size"] == 1
            assert companies_page["total"] == 1
            invalid_page_size = await client.get(
                "/api/v1/companies?page_size=101",
                headers=headers,
            )
            assert invalid_page_size.status_code == 422

            for list_path in (
                "/api/v1/leads?page=1&page_size=10",
                "/api/v1/conversations/messages?page=1&page_size=10",
                "/api/v1/campaigns?page=1&page_size=10",
                "/api/v1/calendar/appointments?page=1&page_size=10",
            ):
                page_response = await client.get(list_path, headers=headers)
                assert page_response.status_code == 200
                assert set(page_response.json()) == {
                    "items",
                    "page",
                    "page_size",
                    "total",
                    "pages",
                }

            dashboard = await client.get("/api/v1/dashboard/summary", headers=headers)
            analytics = await client.get("/api/v1/analytics/overview", headers=headers)
            assert dashboard.status_code == 200
            assert dashboard.json()["messages_drafted"] == 1
            assert analytics.status_code == 200
            assert analytics.json()["rate_counts"]["outreach_dispatch_rate"] == {
                "numerator": 0,
                "denominator": 2,
            }
            assert all(
                integration["status"] in {"configured", "mock", "not_configured"}
                for integration in analytics.json()["integrations_status"].values()
            )

            own_company = await client.get(
                f"/api/v1/companies/{company_a.id}",
                headers=headers,
            )
            foreign_company = await client.get(
                f"/api/v1/companies/{company_b.id}",
                headers=headers,
            )
            assert own_company.status_code == 200
            assert foreign_company.status_code == 404

            foreign_send = await client.post(
                f"/api/v1/leads/messages/{foreign_message.id}/send",
                headers=headers,
            )
            foreign_campaign_execution = await client.post(
                f"/api/v1/campaigns/{foreign_campaign.id}/execute",
                headers=headers,
            )
            foreign_message_execution = await client.post(
                "/api/v1/campaigns/enforcer/execute_message",
                headers=headers,
                json={"message_id": str(foreign_message.id)},
            )
            assert foreign_send.status_code == 404
            assert foreign_campaign_execution.status_code == 404
            assert foreign_message_execution.status_code == 404
            pending_send = await client.post(
                f"/api/v1/leads/messages/{own_pending_message.id}/send",
                headers=headers,
            )
            assert pending_send.status_code == 409

            class MockEmailProvider:
                async def send_email(self, **kwargs):
                    return "test-provider-message-id"

            with patch(
                "app.api.leads.get_email_provider",
                return_value=MockEmailProvider(),
            ):
                own_send = await client.post(
                    f"/api/v1/leads/messages/{own_approved_message.id}/send",
                    headers=headers,
                )
            assert own_send.status_code == 200
            assert own_send.json()["status"] == "sent"

            with patch("app.api.campaigns.celery_app.send_task") as enqueue_campaign:
                own_campaign_execution = await client.post(
                    f"/api/v1/campaigns/{own_campaign.id}/execute",
                    headers=headers,
                )
            assert own_campaign_execution.status_code == 202
            queued_run = own_campaign_execution.json()
            assert queued_run["status"] == "queued"
            enqueue_campaign.assert_called_once()
            queued_record = await async_session.get(
                AgentRun,
                uuid.UUID(queued_run["run_id"]),
            )
            assert queued_record is not None
            assert queued_record.agent_type == "campaign_execution"
            assert queued_record.status == "queued"
            owned_execution_status = await client.get(
                f"/api/v1/campaigns/executions/{queued_run['run_id']}",
                headers=headers,
            )
            assert owned_execution_status.status_code == 200
            assert owned_execution_status.json()["status"] == "queued"

            foreign_run = AgentRun(
                organization_id=org_b.id,
                agent_type="campaign_execution",
                status="queued",
                input_data={"campaign_id": str(foreign_campaign.id)},
            )
            async_session.add(foreign_run)
            await async_session.commit()
            foreign_execution_status = await client.get(
                f"/api/v1/campaigns/executions/{foreign_run.id}",
                headers=headers,
            )
            assert foreign_execution_status.status_code == 404

            with patch(
                "app.api.campaigns.celery_app.send_task",
                side_effect=ConnectionError("broker unavailable"),
            ):
                failed_enqueue = await client.post(
                    f"/api/v1/campaigns/{own_campaign.id}/execute",
                    headers=headers,
                )
            assert failed_enqueue.status_code == 503
            failed_run = (
                await async_session.execute(
                    select(AgentRun).where(
                        AgentRun.agent_type == "campaign_execution",
                        AgentRun.status == "failed",
                    )
                )
            ).scalar_one()
            assert failed_run.error_message == "campaign_queue request failed (ConnectionError)"

            invalid_login = await client.post(
                "/api/v1/auth/login",
                json={"email": user_a.email, "password": "incorrect-password"},
            )
            assert invalid_login.status_code == 401
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_new_campaign_is_created_in_authenticated_organization(
    async_session: AsyncSession,
    jwt_secret,
):
    org = Organization(name="Tenant", slug=f"tenant-{uuid.uuid4().hex}")
    async_session.add(org)
    await async_session.flush()
    user = User(
        organization_id=org.id,
        email=f"{uuid.uuid4().hex}@example.com",
        full_name="Tenant User",
        hashed_password=hash_password("another-test-password-123"),
    )
    async_session.add(user)
    await async_session.commit()

    async def override_get_db():
        yield async_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            login = await client.post(
                "/api/v1/auth/login",
                json={"email": user.email, "password": "another-test-password-123"},
            )
            headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
            response = await client.post(
                "/api/v1/campaigns",
                headers=headers,
                json={"name": "Scoped campaign"},
            )
            assert response.status_code == 201
            campaign = await async_session.scalar(
                select(Campaign).where(Campaign.id == uuid.UUID(response.json()["id"]))
            )
            assert campaign is not None
            assert campaign.organization_id == org.id
    finally:
        app.dependency_overrides.pop(get_db, None)
