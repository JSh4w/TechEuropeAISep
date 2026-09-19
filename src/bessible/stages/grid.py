"""Grid connection assessment stage placeholder."""

from __future__ import annotations

import asyncio
import os

from pydantic import HttpUrl
from temporalio import activity

from bessible.models import Artifact, GridOutput, NodeInput

_demo_failed_runs: set[str] = set()

DEFAULT_QUEUE_POSITION = 42
DEFAULT_TIMESCALE_MONTHS = 36


async def grid_connection(inp: NodeInput) -> GridOutput:
    """Assess National Grid transmission impact and Gate 2 connection timescales."""
    await asyncio.sleep(0)

    # Demo failure injection to demonstrate Temporal activity retries live
    if os.environ.get("BESSIBLE_DEMO_FAIL_ONCE") == "1":
        should_fail = False
        try:
            attempt = activity.info().attempt
            if attempt == 1:
                should_fail = True
        except RuntimeError:
            if inp.run_id not in _demo_failed_runs:
                _demo_failed_runs.add(inp.run_id)
                should_fail = True

        if should_fail:
            msg = "Simulated transient network failure (BESSIBLE_DEMO_FAIL_ONCE=1)"
            raise RuntimeError(msg)

    art = Artifact(
        id=f"grid-{inp.run_id[:8]}",
        stage="grid",
        claim=(
            f"National Grid Gate 2 queue position {DEFAULT_QUEUE_POSITION}, "
            f"indicative connection timescale {DEFAULT_TIMESCALE_MONTHS} months"
        ),
        source_url=HttpUrl("https://www.nationalgrid.com/electricity-transmission"),
        confidence=0.88,
        model_used="dummy",
    )

    return GridOutput(
        gate2_queue_position=DEFAULT_QUEUE_POSITION,
        indicative_connection_months=DEFAULT_TIMESCALE_MONTHS,
        artifacts=[art],
    )
