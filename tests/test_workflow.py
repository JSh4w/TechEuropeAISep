"""End-to-end integration test of AssessmentWorkflow with Suitability Engine."""

from __future__ import annotations

import asyncio
import uuid

import pytest
from temporalio.contrib.pydantic import pydantic_data_converter
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from bessible.activities import ALL_ACTIVITIES
from bessible.models import AssessmentRequest, SiteDecision
from bessible.workflow import TASK_QUEUE, AssessmentWorkflow


@pytest.mark.anyio
async def test_workflow_end_to_end_suitability():
    """Verify full AssessmentWorkflow executes with suitability engine and human confirmation."""
    async with (
        await WorkflowEnvironment.start_time_skipping(data_converter=pydantic_data_converter) as env,
        Worker(
            env.client,
            task_queue=TASK_QUEUE,
            workflows=[AssessmentWorkflow],
            activities=ALL_ACTIVITIES,
        ),
    ):
        handle = await env.client.start_workflow(
            AssessmentWorkflow.run,
            AssessmentRequest(postcode="RH4 1AD", budget_gbp=10_000_000.0),
            id=f"test-wf-{uuid.uuid4().hex[:8]}",
            task_queue=TASK_QUEUE,
        )

        # Wait until awaiting_confirmation
        st = None
        for _ in range(50):
            await asyncio.sleep(0.1)
            st = await handle.query(AssessmentWorkflow.status)
            if st.status == "awaiting_confirmation":
                break
        assert st is not None
        assert st.status == "awaiting_confirmation"

        # Human confirmation update
        await handle.execute_update(
            AssessmentWorkflow.decide_site,
            SiteDecision(confirmed=True, capacity_mw=8.0),
        )

        # Await workflow completion
        result = await handle.result()
        assert result.status == "completed"
        assert result.report is not None
        assert result.report.verdict in ("go", "maybe", "no_go")
        assert len(result.report.findings) >= 2
        assert result.financial is not None
        assert len(result.financial.cases) == 3
        assert result.financial.recommended_h in (2, 4, 8)
        assert len(result.artifacts) >= 10
