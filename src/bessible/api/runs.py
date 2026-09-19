"""FastAPI route handlers for assessment runs."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import JSONResponse
from temporalio.client import WorkflowExecutionStatus

from bessible.api.temporal import get_temporal_client, handle_temporal_error
from bessible.models import AssessmentRequest, AssessmentResult, RunStatus, SiteDecision
from bessible.workflow import TASK_QUEUE, AssessmentWorkflow

router = APIRouter(prefix="/runs", tags=["runs"])

ACTIVE_STATUSES = {"running", "awaiting_confirmation"}
FLOOR_MW = 5.0


@router.post("", status_code=200)
async def start_run(req: AssessmentRequest) -> dict[str, str]:
    """Start an assessment workflow run and return its id."""
    run_id = f"bessible-{uuid.uuid4().hex[:8]}"
    try:
        client = await get_temporal_client()
        await client.start_workflow(
            AssessmentWorkflow.run,
            req,
            id=run_id,
            task_queue=TASK_QUEUE,
        )
    except Exception as exc:
        handle_temporal_error(exc, run_id)
        raise
    else:
        return {"run_id": run_id}


@router.get("/{run_id}/status", response_model=RunStatus)
async def get_run_status(run_id: str) -> RunStatus:
    """Get the current execution status and stage state for a run."""
    try:
        client = await get_temporal_client()
        handle = client.get_workflow_handle(run_id, result_type=AssessmentResult)
        status: RunStatus = await handle.query(AssessmentWorkflow.status)
    except Exception as exc:
        handle_temporal_error(exc, run_id)
        raise
    else:
        return status.model_copy(update={"run_id": run_id})


@router.post("/{run_id}/decision", status_code=204)
async def submit_site_decision(run_id: str, decision: SiteDecision) -> Response:
    """Submit a human-in-the-loop site confirmation or rejection decision."""
    try:
        client = await get_temporal_client()
        handle = client.get_workflow_handle(run_id, result_type=AssessmentResult)
        status: RunStatus = await handle.query(AssessmentWorkflow.status)
    except Exception as exc:
        handle_temporal_error(exc, run_id)
        raise

    if status.status != "awaiting_confirmation":
        raise HTTPException(
            status_code=409,
            detail=f"Run is not awaiting confirmation (current status: {status.status})",
        )

    if decision.confirmed:
        cap = status.capacity
        if cap is None:
            raise HTTPException(
                status_code=400,
                detail="Cannot confirm without a capacity proposal",
            )

        is_flex = bool(decision.flexible_connection)
        allowed_min = FLOOR_MW
        allowed_max = cap.ceiling_mw if is_flex else cap.firm_mw
        chosen_mw = decision.capacity_mw if decision.capacity_mw is not None else cap.recommended_mw

        if chosen_mw < allowed_min or chosen_mw > allowed_max:
            return JSONResponse(
                status_code=422,
                content={
                    "detail": (
                        f"Capacity {chosen_mw:g} MW is out of allowed range [{allowed_min:g}, {allowed_max:g}] MW"
                    ),
                    "allowed_min": allowed_min,
                    "allowed_max": allowed_max,
                },
            )

    try:
        await handle.execute_update(AssessmentWorkflow.decide_site, decision)
    except Exception as exc:
        handle_temporal_error(exc, run_id)
        raise

    return Response(status_code=204)


@router.get("/{run_id}/result", response_model=AssessmentResult)
async def get_run_result(run_id: str) -> AssessmentResult | Response:
    """Get the final assessment result if completed, or 409 if still in progress."""
    try:
        client = await get_temporal_client()
        handle = client.get_workflow_handle(run_id, result_type=AssessmentResult)
        desc = await handle.describe()
        if desc.status == WorkflowExecutionStatus.RUNNING:
            status: RunStatus = await handle.query(AssessmentWorkflow.status)
            return JSONResponse(
                status_code=409,
                content={
                    "detail": f"Run is not finished yet (current status: {status.status})",
                    "status": status.status,
                },
            )

        return await handle.result()
    except Exception as exc:
        handle_temporal_error(exc, run_id)
        raise
