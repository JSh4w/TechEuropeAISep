"""Two runs at once each use only their own Google key, and no key reaches Temporal, logs or results."""

from __future__ import annotations

import asyncio
import base64
import binascii
import contextlib
import json
import logging
import uuid
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from pydantic import SecretStr
from temporalio.client import WorkflowFailureError
from temporalio.contrib.pydantic import pydantic_data_converter
from temporalio.exceptions import ActivityError, ApplicationError
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from bessible.activities import ALL_ACTIVITIES
from bessible.models import AssessmentRequest, SiteDecision
from bessible.workflow import TASK_QUEUE, AssessmentWorkflow

if TYPE_CHECKING:
    from collections.abc import Callable

    from temporalio.client import WorkflowHandle

    from bessible.models import AssessmentResult, EncryptedCredentials
    from tests.conftest import FakeGemini

KEY_A = "AIzaSyKEY-A-0000000000000000000000000"
KEY_B = "AIzaSyKEY-B-1111111111111111111111111"
MASKED = "**********"
MIN_MODELS_PER_RUN = 3  # location, sentiment and planning each build the run's model


def strings_in(node: object) -> list[str]:
    """Every string in a JSON tree, plus the base64-decoded text of any string that decodes (Temporal payloads)."""
    found: list[str] = []
    if isinstance(node, str):
        found.append(node)
        with contextlib.suppress(binascii.Error, ValueError):
            found.append(base64.b64decode(node, validate=True).decode("utf-8", errors="ignore"))
    elif isinstance(node, dict):
        for value in node.values():
            found.extend(strings_in(value))
    elif isinstance(node, list):
        for value in node:
            found.extend(strings_in(value))
    return found


async def start(env: WorkflowEnvironment, credentials: EncryptedCredentials | None) -> WorkflowHandle:
    return await env.client.start_workflow(
        AssessmentWorkflow.run,
        AssessmentRequest(postcode="RH4 1AD", budget_gbp=10_000_000.0, credentials=credentials),
        id=f"test-iso-{uuid.uuid4().hex[:8]}",
        task_queue=TASK_QUEUE,
    )


async def confirm(handle: WorkflowHandle) -> None:
    for _ in range(100):
        await asyncio.sleep(0.1)
        status = await handle.query(AssessmentWorkflow.status)
        if status.status == "awaiting_confirmation":
            await handle.execute_update(
                AssessmentWorkflow.decide_site, SiteDecision(confirmed=True, capacity_mw=status.capacity.recommended_mw)
            )
            return
    pytest.fail("run never reached the confirmation step")


def files_text(result: AssessmentResult) -> str:
    paths = [p for p in Path(result.run_dir).rglob("*") if p.is_file()]
    return "\n".join(p.read_text(encoding="utf-8", errors="ignore") for p in paths)


@pytest.mark.anyio
async def test_concurrent_runs_never_share_a_key(
    fake_gemini: FakeGemini,
    seal: Callable[[str, str], EncryptedCredentials],
    caplog: pytest.LogCaptureFixture,
):
    creds_a, creds_b = seal("user-a", KEY_A), seal("user-b", KEY_B)
    caplog.set_level(logging.DEBUG)
    async with (
        await WorkflowEnvironment.start_time_skipping(data_converter=pydantic_data_converter) as env,
        Worker(env.client, task_queue=TASK_QUEUE, workflows=[AssessmentWorkflow], activities=ALL_ACTIVITIES),
    ):
        handle_a, handle_b = await asyncio.gather(start(env, creds_a), start(env, creds_b))
        await asyncio.gather(confirm(handle_a), confirm(handle_b))
        result_a, result_b = await asyncio.gather(handle_a.result(), handle_b.result())
        history = {
            "a": (await handle_a.fetch_history()).to_json(),
            "b": (await handle_b.fetch_history()).to_json(),
        }

    # Each run built its models only from its own key.
    keys_by_run = defaultdict(list)
    for workflow_id, api_key in fake_gemini.built:
        keys_by_run[workflow_id].append(api_key)
    assert set(keys_by_run) == {handle_a.id, handle_b.id}
    assert set(keys_by_run[handle_a.id]) == {KEY_A}
    assert set(keys_by_run[handle_b.id]) == {KEY_B}
    assert len(keys_by_run[handle_a.id]) >= MIN_MODELS_PER_RUN
    assert len(keys_by_run[handle_b.id]) >= MIN_MODELS_PER_RUN

    # No plaintext key (or masked stand-in) in workflow history; the ciphertext is what travels.
    for name, creds in (("a", creds_a), ("b", creds_b)):
        seen = strings_in(json.loads(history[name]))
        assert not any(KEY_A in s or KEY_B in s or MASKED in s for s in seen)
        assert any(creds.google_ct in s for s in seen)

    # No key in logs, API-facing results or run files.
    everything = "\n".join([
        caplog.text,
        result_a.model_dump_json(),
        result_b.model_dump_json(),
        files_text(result_a),
        files_text(result_b),
    ])
    assert KEY_A not in everything
    assert KEY_B not in everything


@pytest.mark.anyio
async def test_run_without_a_key_fails_and_uses_no_server_key(
    fake_gemini: FakeGemini, seal: Callable[[str, str], EncryptedCredentials], monkeypatch: pytest.MonkeyPatch
):
    seal("unused", "unused")  # sets the master secret, as a server that has keys would
    monkeypatch.setattr("bessible.config.settings.google_api_key", SecretStr("SERVER-KEY"))
    async with (
        await WorkflowEnvironment.start_time_skipping(data_converter=pydantic_data_converter) as env,
        Worker(env.client, task_queue=TASK_QUEUE, workflows=[AssessmentWorkflow], activities=ALL_ACTIVITIES),
    ):
        handle = await start(env, None)
        with pytest.raises(WorkflowFailureError) as failure:
            await handle.result()

    activity_error = failure.value.cause
    assert isinstance(activity_error, ActivityError)
    assert isinstance(activity_error.cause, ApplicationError)
    assert activity_error.cause.type == "MissingGoogleKey"
    assert activity_error.cause.non_retryable is True
    assert fake_gemini.built == []  # no model was ever built, so no server key was used
