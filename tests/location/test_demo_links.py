"""Tests verifying cached demo links resolution offline and end-to-end workflow execution."""

from __future__ import annotations

import asyncio
import uuid
from unittest.mock import patch

import pytest
from pydantic import HttpUrl
from temporalio.contrib.pydantic import pydantic_data_converter
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from bessible.activities import ALL_ACTIVITIES
from bessible.models import AssessmentRequest, LocationInput, SiteDecision
from bessible.stages.location import resolve_location
from bessible.workflow import TASK_QUEUE, AssessmentWorkflow

DEMO_CASES = [
    ("https://example.com/property", "OX14 4TE"),
    ("https://example.com/property/123", "RH4 1AD"),
    ("https://example.com/property/brockham", "RH3 7EZ"),
]


@pytest.mark.anyio
@pytest.mark.parametrize(("demo_url", "expected_postcode"), DEMO_CASES)
async def test_demo_links_resolve_offline(demo_url: str, expected_postcode: str):
    """Verify each demo link resolves to the expected postcode with network off."""
    with (
        patch("httpx.AsyncClient.get", side_effect=RuntimeError("Network is OFF")),
        patch("bessible.location.extract.gemini_model", side_effect=RuntimeError("Network is OFF")),
    ):
        inp = LocationInput(run_id=f"demo-{uuid.uuid4().hex[:6]}", request=AssessmentRequest(link=demo_url))
        loc = await resolve_location(inp)
        assert loc.postcode == expected_postcode
        assert len(loc.artifacts) == 1
        assert str(loc.artifacts[0].source_url) == demo_url


@pytest.mark.anyio
async def test_workflow_end_to_end_with_demo_link_offline():
    """Verify full AssessmentWorkflow executes from a property link offline with auto-confirmation."""
    demo_url = "https://example.com/property/123"

    with (
        patch("httpx.AsyncClient.get", side_effect=RuntimeError("Network is OFF")),
        patch("bessible.location.extract.gemini_model", side_effect=RuntimeError("Network is OFF")),
    ):
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
                AssessmentRequest(property_url=HttpUrl(demo_url), budget_gbp=10_000_000.0),
                id=f"test-demo-wf-{uuid.uuid4().hex[:8]}",
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
            assert st.position is not None

            # Simulate --yes auto confirmation
            await handle.execute_update(
                AssessmentWorkflow.decide_site,
                SiteDecision(confirmed=True, capacity_mw=st.capacity.recommended_mw if st.capacity else 8.0),
            )

            result = await handle.result()
            assert result.status == "completed"
            # Check that location artifact is present with source_url of the demo link
            loc_artifacts = [a for a in result.artifacts if a.stage == "location"]
            assert len(loc_artifacts) >= 1
            assert str(loc_artifacts[0].source_url) == demo_url
