"""Append-only trace event log per run, supporting SSE streaming."""

from __future__ import annotations

import contextlib
import fcntl
import json
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from bessible.config import settings

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)


def get_events_path(run_id: str) -> Path:
    """Return the Path to the events.jsonl file for a run."""
    run_folder = settings.data_dir.parent / "out" / run_id
    return run_folder / "events.jsonl"


def _write_event(events_file: Path, stage: str, message: str) -> None:
    """Append a single event to the opened file under lock."""
    events_file.parent.mkdir(parents=True, exist_ok=True)
    with events_file.open("a+", encoding="utf-8") as f:
        with contextlib.suppress(OSError):
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)

        try:
            f.seek(0)
            lines = [line for line in f if line.strip()]
            next_id = len(lines) + 1
            t = datetime.now(UTC).isoformat()
            event_data = {
                "id": next_id,
                "t": t,
                "stage": stage,
                "msg": message,
            }
            f.seek(0, 2)
            f.write(json.dumps(event_data) + "\n")
            f.flush()
        finally:
            with contextlib.suppress(OSError):
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)


def emit(run_id: str, stage: str, message: str) -> None:
    """Append one JSON line to out/<run_id>/events.jsonl. Never raises."""
    try:
        events_file = get_events_path(run_id)
        _write_event(events_file, stage, message)
    except Exception as exc:  # ruff: ignore[blind-except]
        logger.warning("Failed to emit trace event for run %s: %s", run_id, exc)
