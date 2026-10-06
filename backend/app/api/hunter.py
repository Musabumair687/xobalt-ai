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

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.dependencies import get_db
from app.schemas.hunter import HunterCriteria, HunterResult, HunterRunStatus
from app.workflows.hunter_workflow import build_hunter_graph, get_initial_state

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
    db: AsyncSession = Depends(get_db),
) -> HunterResult:
    """Trigger a Hunter workflow run for the given ICP criteria.

    The workflow runs asynchronously (via BackgroundTasks in Phase 3).
    In Phase 7+ this will be dispatched to a Celery/ARQ worker.

    Returns an immediate HunterResult with status=running and a run_id
    so the caller can poll for progress.
    """
    run_id = uuid.uuid4()
    logger.info(
        "Hunter run requested | run_id=%s industry=%s country=%s",
        run_id,
        criteria.industry,
        criteria.country,
    )

    initial_state = get_initial_state(criteria.model_dump())

    async def _run() -> None:
        try:
            graph = build_hunter_graph(db=db)
            final_state = await graph.ainvoke(initial_state)
            logger.info(
                "Hunter run %s complete | leads=%d errors=%d",
                run_id,
                len(final_state.get("lead_ids", [])),
                len(final_state.get("errors", [])),
            )
        except Exception as exc:
            logger.error("Hunter run %s failed: %s", run_id, exc, exc_info=True)

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
async def get_hunter_status(run_id: uuid.UUID) -> dict[str, Any]:
    """Placeholder endpoint for run status.

    In Phase 7 this will query the agent_runs table.
    For now it returns a static response.
    """
    return {
        "run_id": str(run_id),
        "status": "status_tracking_available_in_phase7",
    }
