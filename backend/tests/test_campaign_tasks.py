import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_run import AgentRun
from app.models.organization import Organization
from app.workers import campaign_tasks


@pytest.mark.asyncio
async def test_campaign_task_persists_completion_and_message_snapshot(
    async_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    organization = Organization(
        name="Queue Test",
        slug=f"queue-{uuid.uuid4().hex}",
    )
    async_session.add(organization)
    await async_session.flush()

    campaign_id = uuid.uuid4()
    message_id = uuid.uuid4()
    run = AgentRun(
        organization_id=organization.id,
        agent_type="campaign_execution",
        status="queued",
        input_data={"campaign_id": str(campaign_id)},
        output_data={"retry_count": 1},
    )
    async_session.add(run)
    await async_session.commit()

    class SessionContext:
        async def __aenter__(self):
            return async_session

        async def __aexit__(self, *_args):
            return None

    class FakeCampaignService:
        def __init__(self, _db):
            pass

        async def get_approved_message_ids(self, received_campaign_id, received_org_id):
            assert received_campaign_id == campaign_id
            assert received_org_id == organization.id
            return [message_id]

        async def process_campaign_outreach(
            self,
            received_campaign_id,
            received_org_id,
            *,
            message_ids,
        ):
            assert received_campaign_id == campaign_id
            assert received_org_id == organization.id
            assert message_ids == [message_id]
            return {
                "selected": 1,
                "sent": 1,
                "blocked": 0,
                "failed": 0,
                "skipped": 0,
            }

    monkeypatch.setattr(campaign_tasks, "AsyncSessionLocal", SessionContext)
    monkeypatch.setattr(campaign_tasks, "CampaignService", FakeCampaignService)

    await campaign_tasks._execute_campaign(run.id, campaign_id, organization.id)

    await async_session.refresh(run)
    assert run.status == "completed"
    assert run.input_data["message_ids"] == [str(message_id)]
    assert run.output_data == {
        "selected": 1,
        "sent": 1,
        "blocked": 0,
        "failed": 0,
        "skipped": 0,
        "retry_count": 1,
    }
    assert run.completed_at is not None
    assert run.duration_seconds is not None
