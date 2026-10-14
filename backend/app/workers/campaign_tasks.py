"""Celery task entry points for campaign execution."""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from app.database.session import AsyncSessionLocal
from app.integrations.provider_errors import ProviderConfigurationError
from app.models.agent_run import AgentRun
from app.services.campaign_service import CampaignService
from app.workers.celery_app import celery_app
from app.services.integration_settings_service import organization_settings_scope

logger = logging.getLogger(__name__)
CAMPAIGN_TASK_NAME = "app.workers.campaign_tasks.execute_campaign"


def _duration_seconds(started_at: datetime, completed_at: datetime) -> float:
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=timezone.utc)
    return max(0.0, (completed_at - started_at).total_seconds())


async def _execute_campaign(run_id: uuid.UUID, campaign_id: uuid.UUID, organization_id: uuid.UUID) -> None:
    async with AsyncSessionLocal() as db:
        run = await db.get(AgentRun, run_id)
        if run is None:
            raise LookupError("Campaign execution record not found.")
        if run.status == "completed":
            return

        run.status = "running"
        run.error_message = None
        await db.commit()

        campaign_service = CampaignService(db)
        input_data = dict(run.input_data or {})
        if "message_ids" not in input_data:
            selected_ids = await campaign_service.get_approved_message_ids(
                campaign_id,
                organization_id,
            )
            input_data["message_ids"] = [str(message_id) for message_id in selected_ids]
            run.input_data = input_data
            await db.commit()
        else:
            selected_ids = [uuid.UUID(item) for item in input_data["message_ids"]]

        async with organization_settings_scope(db, organization_id):
            counts = await campaign_service.process_campaign_outreach(
                campaign_id,
                organization_id,
                message_ids=selected_ids,
            )
        retry_count = (run.output_data or {}).get("retry_count", 0)
        completed_at = datetime.now(timezone.utc)
        run.status = "failed" if counts["failed"] else "completed"
        run.output_data = {**counts, "retry_count": retry_count}
        run.error_message = (
            "One or more message sends failed; inspect message status and send_error."
            if counts["failed"]
            else None
        )
        run.completed_at = completed_at
        run.duration_seconds = _duration_seconds(run.started_at, completed_at)
        await db.commit()


async def _update_retry_status(run_id: uuid.UUID, retries: int, terminal: bool, error: Exception) -> None:
    async with AsyncSessionLocal() as db:
        run = await db.get(AgentRun, run_id)
        if run is None:
            return
        run.status = "failed" if terminal else "retrying"
        run.error_message = f"Campaign worker failed ({type(error).__name__})."
        output = dict(run.output_data or {})
        output["retry_count"] = retries
        run.output_data = output
        if terminal:
            completed_at = datetime.now(timezone.utc)
            run.completed_at = completed_at
            run.duration_seconds = _duration_seconds(run.started_at, completed_at)
        else:
            run.completed_at = None
            run.duration_seconds = None
        await db.commit()


@celery_app.task(
    bind=True,
    name=CAMPAIGN_TASK_NAME,
    max_retries=3,
    default_retry_delay=5,
)
def execute_campaign(
    self: Any,
    run_id: str,
    campaign_id: str,
    organization_id: str,
) -> None:
    """Execute a campaign outside the API process and retry safe infrastructure failures."""
    run_uuid = uuid.UUID(run_id)
    try:
        asyncio.run(
            _execute_campaign(
                run_uuid,
                uuid.UUID(campaign_id),
                uuid.UUID(organization_id),
            )
        )
    except ProviderConfigurationError as exc:
        asyncio.run(_update_retry_status(run_uuid, self.request.retries, True, exc))
        logger.error("Campaign run %s failed due to provider configuration.", run_id)
        raise
    except Exception as exc:
        terminal = self.request.retries >= self.max_retries
        asyncio.run(
            _update_retry_status(
                run_uuid,
                self.request.retries + 1,
                terminal,
                exc,
            )
        )
        logger.error(
            "Campaign run %s failed on worker attempt %d (%s).",
            run_id,
            self.request.retries + 1,
            type(exc).__name__,
        )
        if not terminal:
            raise self.retry(exc=exc)
        raise
