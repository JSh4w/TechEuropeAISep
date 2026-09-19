from __future__ import annotations

from datetime import date

import pytest

from bessible.models import (
    AssessmentRequest,
    CapacityOutput,
    ConfirmedSite,
    GridOutput,
    PlanningInput,
    Position,
    SiteLandOutput,
    TitleOutput,
)
from bessible.planning.tia import tia_statement
from bessible.stages.planning import regulatory_planning


def test_tia_statement_threshold_5_at_5mw():
    s = tia_statement(threshold_mw=5, capacity_mw=5.0)
    assert s.threshold_mw == 5
    assert s.triggered is True
    assert "Transmission Impact Assessment (TIA) triggered" in s.statement
    assert "5 MW threshold" in s.statement
    assert "NESO involvement and Gate 2 timescales apply" in s.statement


def test_tia_statement_threshold_1_at_8mw():
    s = tia_statement(threshold_mw=1, capacity_mw=8.0, snapshot_date=date(2026, 9, 1))
    assert s.threshold_mw == 1
    assert s.triggered is True
    assert "Transmission Impact Assessment (TIA) triggered" in s.statement
    assert "1 MW threshold" in s.statement
    assert "dated 2026-09-01" in s.statement


def test_tia_statement_below_threshold():
    s = tia_statement(threshold_mw=5, capacity_mw=4.0)
    assert s.threshold_mw == 5
    assert s.triggered is False
    assert "not triggered" in s.statement


def test_tia_statement_unknown_threshold():
    s = tia_statement(threshold_mw=None, capacity_mw=10.0)
    assert s.threshold_mw is None
    assert s.triggered is None
    assert "threshold is unknown" in s.statement


@pytest.mark.anyio
async def test_stage_includes_tia_artifact_and_field():
    inp = PlanningInput.model_construct(
        run_id="tiarun-1234",
        request=AssessmentRequest(postcode="RH4 1AD"),
        site=ConfirmedSite.model_construct(
            position=Position(lat=51.23, lon=-0.33),
            capacity_mw=6.0,
            boundary=TitleOutput.model_construct(),
            capacity=None,
            flexible_connection=False,
        ),
        capacity=CapacityOutput.model_construct(tia_threshold_mw=5),
        grid=GridOutput(),
        site_land=SiteLandOutput(land_use="Agricultural", constraints=[], artifacts=[]),
    )

    out = await regulatory_planning(inp)
    assert out.tia is not None
    assert out.tia.threshold_mw == 5
    assert out.tia.triggered is True

    tia_artifacts = [a for a in out.artifacts if a.id.startswith("planning-tia-")]
    assert len(tia_artifacts) == 1
    assert "Transmission Impact Assessment (TIA) triggered" in tia_artifacts[0].claim
