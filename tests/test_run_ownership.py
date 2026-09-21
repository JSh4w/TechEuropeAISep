"""POST /runs attaches the caller's encrypted key and owner; every /runs/{id} route serves only the owner."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from temporalio.client import WorkflowExecutionStatus

from bessible import events
from bessible.api.app import app
from bessible.auth import User, current_user
from bessible.keystore import Keyring, KeyStore, get_key_store
from bessible.models import AssessmentResult, CapacityOutput, RunStatus

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

ALICE_KEY = "AIza" + "A" * 35
BOB_KEY = "AIza" + "B" * 35
RUN = {"postcode": "RH4 1AD", "battery_mw": 8.0}
UUID4_ID = re.compile(r"^bessible-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")


@pytest.fixture
def store(tmp_path: Path) -> KeyStore:
    return KeyStore(tmp_path / "keys.db", Keyring("k1", {"k1": b"secret"}))


def _as(uid: str) -> None:
    app.dependency_overrides[current_user] = lambda: User(uid=uid)


@pytest.fixture
def client(store: KeyStore) -> Iterator[TestClient]:
    app.dependency_overrides[get_key_store] = lambda: store
    _as("alice")
    yield TestClient(app)
    app.dependency_overrides.clear()


def _temporal(owner: str | None, *, running: bool = False) -> tuple[AsyncMock, MagicMock, MagicMock]:
    """A patched Temporal client with one run owned by `owner`."""
    desc = MagicMock()
    desc.status = WorkflowExecutionStatus.RUNNING if running else WorkflowExecutionStatus.COMPLETED
    desc.memo_value = AsyncMock(return_value=owner)
    handle = MagicMock()
    handle.describe = AsyncMock(return_value=desc)
    handle.query = AsyncMock(
        return_value=RunStatus(
            status="awaiting_confirmation",
            stages=[],
            capacity=CapacityOutput(viable=True, firm_mw=8.0, ceiling_mw=12.0, recommended_mw=8.0),
        )
    )
    handle.result = AsyncMock(return_value=AssessmentResult(status="completed", run_dir="out/x"))
    handle.execute_update = AsyncMock(return_value=None)
    temporal = MagicMock()
    temporal.get_workflow_handle.return_value = handle
    temporal.start_workflow = AsyncMock(return_value=handle)
    return AsyncMock(return_value=temporal), temporal, handle


class TestStartRun:
    def test_without_key_is_401_and_starts_nothing(self, client: TestClient) -> None:
        getter, temporal, _ = _temporal("alice")
        with patch("bessible.api.runs.get_temporal_client", getter):
            res = client.post("/runs", json=RUN)
        assert res.status_code == 401
        assert res.json()["detail"] == "missing_google_key"
        temporal.start_workflow.assert_not_called()

    def test_after_key_deleted_is_401_again(self, client: TestClient, store: KeyStore) -> None:
        store.put("alice", ALICE_KEY)
        store.delete("alice")
        getter, temporal, _ = _temporal("alice")
        with patch("bessible.api.runs.get_temporal_client", getter):
            assert client.post("/runs", json=RUN).status_code == 401
        temporal.start_workflow.assert_not_called()

    def test_attaches_owner_and_ciphertext_only(self, client: TestClient, store: KeyStore) -> None:
        store.put("alice", ALICE_KEY)
        getter, temporal, _ = _temporal("alice")
        with patch("bessible.api.runs.get_temporal_client", getter):
            res = client.post("/runs", json=RUN)
        assert res.status_code == 200
        run_id = res.json()["run_id"]
        assert UUID4_ID.match(run_id)

        call = temporal.start_workflow.await_args
        assert call.kwargs["id"] == run_id
        assert call.kwargs["memo"] == {"owner_uid": "alice"}
        sent = call.args[1]
        assert sent.credentials == store.credentials("alice")
        assert sent.credentials.uid == "alice"
        assert ALICE_KEY not in sent.model_dump_json()
        assert ALICE_KEY not in res.text

    def test_client_supplied_credentials_are_ignored(self, client: TestClient, store: KeyStore) -> None:
        store.put("alice", ALICE_KEY)
        store.put("bob", BOB_KEY)
        bobs = store.credentials("bob").model_dump()
        getter, temporal, _ = _temporal("alice")
        with patch("bessible.api.runs.get_temporal_client", getter):
            res = client.post("/runs", json={**RUN, "credentials": bobs})
        assert res.status_code == 200
        assert temporal.start_workflow.await_args.args[1].credentials.uid == "alice"
        assert temporal.start_workflow.await_args.args[1].credentials == store.credentials("alice")

    def test_ids_do_not_repeat(self, client: TestClient, store: KeyStore) -> None:
        store.put("alice", ALICE_KEY)
        getter, _, _ = _temporal("alice")
        with patch("bessible.api.runs.get_temporal_client", getter):
            ids = {client.post("/runs", json=RUN).json()["run_id"] for _ in range(5)}
        assert len(ids) == 5

    def test_undecryptable_stored_key_does_not_start_a_run(self, client: TestClient, store: KeyStore) -> None:
        import sqlite3

        store.put("alice", ALICE_KEY)
        store.put("bob", BOB_KEY)
        with sqlite3.connect(store._path) as conn:  # ruff: ignore[private-member-access]
            conn.execute(
                "UPDATE user_keys SET ciphertext = (SELECT ciphertext FROM user_keys WHERE uid='bob') WHERE uid='alice'"
            )
        getter, temporal, _ = _temporal("alice")
        with patch("bessible.api.runs.get_temporal_client", getter):
            res = client.post("/runs", json=RUN)
        assert res.status_code == 409
        temporal.start_workflow.assert_not_called()


class TestOwnership:
    """The same run id is invisible to anyone but its owner: 404, never 403."""

    @pytest.fixture(autouse=True)  # ruff: ignore[pytest-fixture-autouse] - applies to every test here
    def _bob_owns_the_run(self) -> None:
        # The caller is alice (the `client` fixture); the run belongs to bob.
        pass

    def _calls(self, client: TestClient) -> list[Any]:
        return [
            client.get("/runs/bessible-1/status"),
            client.post("/runs/bessible-1/decision", json={"confirmed": True, "capacity_mw": 8.0}),
            client.get("/runs/bessible-1/result"),
            client.get("/runs/bessible-1/events"),
        ]

    def test_other_users_run_is_404_on_every_route(self, client: TestClient) -> None:
        getter, _, handle = _temporal("bob")
        with (
            patch("bessible.api.runs.get_temporal_client", getter),
            patch("bessible.api.events.get_temporal_client", getter),
        ):
            responses = self._calls(client)
        assert [r.status_code for r in responses] == [404, 404, 404, 404]
        assert {r.text for r in responses[:3]} == {'{"detail":"Run \'bessible-1\' not found"}'}
        handle.execute_update.assert_not_called()
        handle.query.assert_not_called()
        handle.result.assert_not_called()

    def test_run_without_owner_memo_is_404(self, client: TestClient) -> None:
        getter, _, _ = _temporal(None)
        with (
            patch("bessible.api.runs.get_temporal_client", getter),
            patch("bessible.api.events.get_temporal_client", getter),
        ):
            assert [r.status_code for r in self._calls(client)] == [404, 404, 404, 404]

    def test_owner_is_served(self, client: TestClient) -> None:
        getter, _, handle = _temporal("alice", running=True)
        with patch("bessible.api.runs.get_temporal_client", getter):
            assert client.get("/runs/bessible-1/status").status_code == 200
            assert (
                client.post("/runs/bessible-1/decision", json={"confirmed": True, "capacity_mw": 8.0}).status_code
                == 204
            )
            assert client.get("/runs/bessible-1/result").status_code == 409  # running: served to the owner
        handle.execute_update.assert_awaited_once()

    def test_completed_result_only_for_owner(self, client: TestClient) -> None:
        getter, _, _ = _temporal("alice")
        with patch("bessible.api.runs.get_temporal_client", getter):
            assert client.get("/runs/bessible-1/result").status_code == 200
        _as("mallory")
        with patch("bessible.api.runs.get_temporal_client", getter):
            assert client.get("/runs/bessible-1/result").status_code == 404

    def test_events_of_other_users_run_do_not_leak(self, client: TestClient) -> None:
        run_id = "bessible-ownership-events-test"
        events.emit(run_id, "location", "alice-only secret trace")
        path = events.get_events_path(run_id)
        try:
            getter, _, _ = _temporal("alice")
            with patch("bessible.api.events.get_temporal_client", getter):
                assert "alice-only secret trace" in client.get(f"/runs/{run_id}/events").text
                _as("mallory")
                res = client.get(f"/runs/{run_id}/events")
            assert res.status_code == 404
            assert "secret" not in res.text
        finally:
            path.unlink(missing_ok=True)
            path.parent.rmdir()

    def test_events_fail_closed_when_temporal_is_down(self, client: TestClient) -> None:
        run_id = "bessible-ownership-down-test"
        events.emit(run_id, "location", "trace")
        path = events.get_events_path(run_id)
        try:
            with patch("bessible.api.events.get_temporal_client", side_effect=OSError("refused")):
                assert client.get(f"/runs/{run_id}/events").status_code == 503
        finally:
            path.unlink(missing_ok=True)
            path.parent.rmdir()
