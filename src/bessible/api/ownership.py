"""Run ownership: a run is served only to the `uid` that started it."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastapi import HTTPException

if TYPE_CHECKING:
    from temporalio.client import WorkflowExecutionDescription, WorkflowHandle

    from bessible.auth import User

OWNER_MEMO = "owner_uid"


async def assert_owner(handle: WorkflowHandle[Any, Any], run_id: str, user: User) -> WorkflowExecutionDescription:
    """Return the run's description, or 404 (never 403, so ids are not confirmed) if `user` did not start it.

    A missing run raises the Temporal not-found error; the caller maps it to 404 the same way.
    """
    desc = await handle.describe()
    owner = await desc.memo_value(OWNER_MEMO, None)
    if owner is None or owner != user.uid:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    return desc
