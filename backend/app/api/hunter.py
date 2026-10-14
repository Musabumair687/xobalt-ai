"""Hunter API router.

Provides:
    POST /api/v1/hunter/run   → start a Hunter workflow run
    GET  /api/v1/hunter/status/{run_id}  → placeholder for run status

The API is intentionally thin — it validates the request and triggers
the workflow.  All business logic lives in the workflow and services.
"""

from __future__ import annotations

import uuid
import logging
from typing import Any
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.dependencies import get_db
from app.database.session import AsyncSessionLocal
from app.schemas.hunter import HunterCriteria, HunterResult, HunterRunStatus
from app.workflows.hunter_workflow import build_hunter_graph, get_initial_state
from app.models.campaign import Campaign
from app.models.agent_run import AgentRun
from app.models.user import User
from app.auth import get_current_user
from sqlalchemy import select
from app.integrations.provider_errors import safe_provider_error
from app.services.integration_settings_service import organization_settings_scope

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/hunter", tags=["Hunter"])


# ---------------------------------------------------------------------------
# Endpoint: Run Hunter
# ---------------------------------------------------------------------------


@router.post(
    "/run",
    response_model=HunterResult,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start a Hunter workflow run",
)
async def run_hunter(
    criteria: HunterCriteria,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HunterResult:
    """Trigger a Hunter workflow run for the given ICP criteria.

    The workflow runs asynchronously (via BackgroundTasks in Phase 3).
    In Phase 7+ this will be dispatched to a Celery/ARQ worker.

    Returns an immediate HunterResult with status=running and a run_id
    so the caller can poll for progress.
    """
    criteria = criteria.model_copy(
        update={"organization_id": current_user.organization_id}
    )
    if criteria.campaign_id is not None:
        campaign_res = await db.execute(
            select(Campaign.id).where(
                Campaign.id == criteria.campaign_id,
                Campaign.organization_id == current_user.organization_id,
            )
        )
        if campaign_res.scalar_one_or_none() is None:
            raise HTTPException(status_code=404, detail="Campaign not found")

    run_id = uuid.uuid4()
    logger.info(
        "Hunter run requested | run_id=%s industry=%s country=%s",
        run_id,
        criteria.industry,
        criteria.country,
    )

    initial_state = get_initial_state(criteria.model_dump())
    run = AgentRun(
        id=run_id,
        organization_id=current_user.organization_id,
        agent_type="hunter",
        status="running",
        started_at=datetime.now(timezone.utc),
        input_data={
            "industry": criteria.industry,
            "country": criteria.country,
            "max_companies": criteria.max_companies,
            "campaign_id": str(criteria.campaign_id) if criteria.campaign_id else None,
        },
        triggered_by=str(current_user.id),
        output_data={"steps": {}, "lead_ids": []},
    )
    db.add(run)
    await db.commit()

    async def _run() -> None:
        async with AsyncSessionLocal() as task_db:
            task_run = await task_db.get(AgentRun, run_id)
            if task_run is None:
                logger.error("Hunter run record %s disappeared before execution.", run_id)
                return
            try:
                graph = build_hunter_graph(db=task_db)
                async with organization_settings_scope(
                    task_db,
                    current_user.organization_id,
                ):
                    final_state = await graph.ainvoke(initial_state)
                steps = final_state.get("steps", {})
                failed = any(
                    step.get("status") == "failed" for step in steps.values()
                )
                task_run.status = "failed" if failed else "completed"
                task_run.output_data = {
                    "steps": steps,
                    "lead_ids": [str(lead_id) for lead_id in final_state.get("lead_ids", [])],
                    "lead_count": len(final_state.get("lead_ids", [])),
                    "errors": final_state.get("errors", []),
                }
                if failed:
                    task_run.error_message = "One or more Hunter steps failed; see step details."
            except Exception as exc:
                safe_error = safe_provider_error("hunter_pipeline", exc)
                task_run.status = "failed"
                task_run.error_message = str(safe_error)
                task_run.output_data = {
                    "steps": {
                        "pipeline": {
                            "status": "failed",
                            "error_type": safe_error.error_type,
                            "message": str(safe_error),
                        }
                    },
                    "lead_ids": [],
                    "lead_count": 0,
                }
                logger.error("Hunter run %s failed (%s).", run_id, safe_error.error_type)
            finally:
                task_run.completed_at = datetime.now(timezone.utc)
                started_at = task_run.started_at
                if started_at.tzinfo is None:
                    started_at = started_at.replace(tzinfo=timezone.utc)
                task_run.duration_seconds = max(
                    0.0, (task_run.completed_at - started_at).total_seconds()
                )
                task_db.add(task_run)
                await task_db.commit()
            logger.info("Hunter run %s finished with status %s.", run_id, task_run.status)

    background_tasks.add_task(_run)

    return HunterResult(
        run_id=run_id,
        status=HunterRunStatus.running,
        criteria=criteria,
    )


# ---------------------------------------------------------------------------
# Endpoint: Status (placeholder)
# ---------------------------------------------------------------------------


@router.get(
    "/status/{run_id}",
    summary="Get Hunter run status (placeholder)",
)
async def get_hunter_status(
    run_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Return the run state and safe stage details to its owning organization."""
    run_result = await db.execute(
        select(AgentRun).where(
            AgentRun.id == run_id,
            AgentRun.organization_id == current_user.organization_id,
            AgentRun.agent_type.in_(["hunter", "lead_pipeline"]),
        )
    )
    run = run_result.scalars().first()
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return {
        "run_id": str(run.id),
        "status": run.status,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "duration_seconds": run.duration_seconds,
        "output": run.output_data or {},
        "error": run.error_message,
    }
