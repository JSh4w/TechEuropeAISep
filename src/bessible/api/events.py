"""Server-Sent Events (SSE) endpoint for streaming run progress trace."""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import StreamingResponse
from temporalio.client import WorkflowExecutionStatus

from bessible.api.ownership import assert_owner
from bessible.api.temporal import get_temporal_client, handle_temporal_error
from bessible.auth import User, current_user
from bessible.events import get_events_path

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator
    from pathlib import Path
    from typing import Any

    from temporalio.client import WorkflowHandle

router = APIRouter(tags=["events"])
logger = logging.getLogger(__name__)

POLL_INTERVAL_S = 0.3
MAX_IDLE_CYCLES = 3


def _read_new_events(events_file: Path, after_id: int) -> list[tuple[int, str]]:
    """Read lines from events file with id greater than after_id."""
    results: list[tuple[int, str]] = []
    if not events_file.exists():
        return results

    try:
        content = events_file.read_text(encoding="utf-8")
    except OSError:
        return results

    for raw_line in content.splitlines():
        trimmed = raw_line.strip()
        if not trimmed:
            continue
        with contextlib.suppress(json.JSONDecodeError, KeyError, TypeError):
            payload = json.loads(trimmed)
            eid = int(payload.get("id", 0))
            if eid > after_id:
                results.append((eid, trimmed))

    return results


async def _check_workflow_completed(handle: WorkflowHandle[Any, Any] | None) -> bool:
    """Return True if the workflow handle indicates execution has finished."""
    if handle is None:
        return False
    try:
        desc = await handle.describe()
    except Exception:  # ruff: ignore[blind-except]
        return False
    else:
        return desc.status != WorkflowExecutionStatus.RUNNING


async def event_generator(run_id: str, last_event_id: int) -> AsyncGenerator[str]:
    """Tail events.jsonl and stream events as SSE until workflow completion.

    Yields:
        Formatted SSE data messages with IDs.
    """
    events_file = get_events_path(run_id)
    last_id = last_event_id

    handle: WorkflowHandle[Any, Any] | None = None
    try:
        client = await get_temporal_client()
        handle = client.get_workflow_handle(run_id)
    except Exception:  # ruff: ignore[blind-except]
        handle = None

    idle_cycles = 0

    while True:
        new_events = _read_new_events(events_file, last_id)
        if new_events:
            idle_cycles = 0
            for eid, line in new_events:
                yield f"id: {eid}\ndata: {line}\n\n"
                last_id = eid
        else:
            idle_cycles += 1

        is_done = await _check_workflow_completed(handle)
        if handle is None and idle_cycles >= MAX_IDLE_CYCLES:
            is_done = True

        if is_done:
            trailing = _read_new_events(events_file, last_id)
            for eid, line in trailing:
                yield f"id: {eid}\ndata: {line}\n\n"
                last_id = eid
            break

        await asyncio.sleep(POLL_INTERVAL_S)


@router.get("/runs/{run_id}/events")
async def stream_run_events(
    run_id: str,
    user: Annotated[User, Depends(current_user)],
    last_event_id_header: Annotated[str | None, Header(alias="Last-Event-ID")] = None,
    last_event_id_query: Annotated[int | None, Query(alias="last_event_id")] = None,
) -> StreamingResponse:
    """Stream live trace events for a run using Server-Sent Events, to the run's owner only."""
    if run_id.startswith("demo-"):
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    try:
        client = await get_temporal_client()
        await assert_owner(client.get_workflow_handle(run_id), run_id, user)
    except Exception as exc:
        handle_temporal_error(exc, run_id)
        raise

    start_id = 0
    if last_event_id_header is not None and last_event_id_header.isdigit():
        start_id = int(last_event_id_header)
    elif last_event_id_query is not None:
        start_id = last_event_id_query

    return StreamingResponse(
        event_generator(run_id, start_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
