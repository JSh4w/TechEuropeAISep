"""Temporal worker executing BESS site assessment workflow and activities."""

from __future__ import annotations

import asyncio
import contextlib

from pydantic_ai.durable_exec.temporal import PydanticAIPlugin
from temporalio.client import Client
from temporalio.contrib.pydantic import pydantic_data_converter
from temporalio.worker import Worker

from bessible.activities import ALL_ACTIVITIES
from bessible.config import settings
from bessible.workflow import TASK_QUEUE, AssessmentWorkflow


async def run_worker() -> None:
    """Connect to Temporal and run the worker."""
    client = await Client.connect(
        settings.temporal_address,
        namespace=settings.temporal_namespace,
        data_converter=pydantic_data_converter,
        plugins=[PydanticAIPlugin()],
    )
    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[AssessmentWorkflow],
        activities=ALL_ACTIVITIES,
    )
    print(f"Worker listening on task queue '{TASK_QUEUE}' at {settings.temporal_address}...")  # ruff: ignore[print]
    await worker.run()


def main() -> None:
    """Entry point for the worker process."""
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(run_worker())


if __name__ == "__main__":
    main()
