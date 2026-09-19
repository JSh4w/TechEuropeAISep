"""Run the Temporal worker: `uv run python sandbox/map_session/worker.py` (from the repo root)."""

from __future__ import annotations

import asyncio

import activities
from temporalio.client import Client
from temporalio.contrib.pydantic import pydantic_data_converter
from temporalio.worker import Worker
from workflow import TASK_QUEUE, AssessWorkflow

from bessible.config import settings


async def main() -> None:
    """Connect to Temporal and run the worker until interrupted."""
    client = await Client.connect(
        settings.temporal_address, namespace=settings.temporal_namespace, data_converter=pydantic_data_converter
    )
    print(f"Worker listening on '{TASK_QUEUE}' at {settings.temporal_address}")  # ruff: ignore[print]
    await Worker(client, task_queue=TASK_QUEUE, workflows=[AssessWorkflow], activities=activities.ALL).run()


if __name__ == "__main__":
    asyncio.run(main())
