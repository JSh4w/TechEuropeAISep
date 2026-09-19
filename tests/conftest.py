from __future__ import annotations

import pytest

from bessible.planning.route import LpaLookup


@pytest.fixture(autouse=True)  # ruff: ignore[pytest-fixture-autouse] - every stage test must stay offline
def offline_lpa_lookup(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep stage tests off the network; route tests exercise lookup_lpa with a mock transport."""

    async def fake(*_args: object, **_kwargs: object) -> LpaLookup:
        return LpaLookup(entity=626002, reference="E60000002", name="Darlington LPA")

    monkeypatch.setattr("bessible.stages.planning.lookup_lpa", fake)
