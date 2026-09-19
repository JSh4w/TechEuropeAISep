"""Unit tests for the narration guard."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from bessible.guard import check_narration, guarded
from bessible.models import (
    AssessmentRequest,
    CapacityOutput,
    ConfirmedSite,
    DurationCase,
    FinancialOutput,
    GridOutput,
    MarketOutput,
    PlanningOutput,
    Position,
    SiteLandOutput,
    SynthesisInput,
    TitleOutput,
)
from bessible.stages.synthesis import flatten_state, synthesise


def test_check_narration():
    state = {
        "npv": 1_204_000.0,
        "irr": 0.13,
        "capacity_mw": 20.0,
        "distance_km": 1.5,
    }

    # Matching figures pass
    text_ok = "The 20 MW project achieves an NPV of £1.2m with 13% IRR over 1.5 km."
    assert check_narration(text_ok, state) == []

    # Invented figures fail and are returned
    text_bad = "The 50 MW project achieves an NPV of £5m with 25% IRR."
    unmatched = check_narration(text_bad, state)
    assert len(unmatched) > 0


@pytest.mark.anyio
async def test_guarded_retry_and_fallback():
    state = {"capacity_mw": 20.0, "npv": 100_000.0}
    template = "Fallback: 20 MW project has £100,000 NPV."

    attempts = 0

    async def narrator_recovering(_hint: str | None) -> str:
        nonlocal attempts
        await asyncio.sleep(0)
        attempts += 1
        if attempts == 1:
            return "Invented: 99 MW project with £999k NPV."
        return "Correct: 20 MW project with £100,000 NPV."

    res = await guarded(narrator_recovering, state, template)
    assert "20 MW" in res
    assert attempts == 2

    # Failing narrator falls back to template
    async def narrator_always_failing(_hint: str | None) -> str:
        await asyncio.sleep(0)
        return "Always bad: 500 MW."

    res_fallback = await guarded(narrator_always_failing, state, template)
    assert res_fallback == template


@pytest.mark.anyio
async def test_guard_applied_in_synthesis():
    run_id = "test-synth-guard"
    req = AssessmentRequest(postcode="RH4 1AD")
    cap = CapacityOutput(viable=True, firm_mw=8.0, ceiling_mw=16.0, recommended_mw=12.0)
    title = TitleOutput(title_number="SY1", area_m2=1000.0, boundary_geojson={"type": "Polygon", "coordinates": []})
    site = ConfirmedSite(position=Position(lat=51.2, lon=-0.3), capacity_mw=12.0, boundary=title)
    grid = GridOutput()
    land = SiteLandOutput(land_use="Industrial")
    market = MarketOutput(revenue_gbp_per_mw_year=90000.0)
    fin = FinancialOutput(
        cases=[
            DurationCase(duration_h=2, capex_gbp=6_000_000.0, npv_gbp=500_000.0, irr=0.10),
            DurationCase(duration_h=4, capex_gbp=10_000_000.0, npv_gbp=-500_000.0, irr=0.04),
            DurationCase(duration_h=8, capex_gbp=18_000_000.0, npv_gbp=-5_000_000.0, irr=None),
        ]
    )
    plan = PlanningOutput(consenting_route="LPA", risks=[])

    synth_in = SynthesisInput(
        run_id=run_id,
        request=req,
        site=site,
        capacity=cap,
        grid=grid,
        site_land=land,
        market=market,
        financial=fin,
        planning=plan,
        artifacts=[],
    )

    state = flatten_state(synth_in)
    assert state["capacity_mw"] == 12.0
    assert state["capex_2h"] == 6_000_000.0

    out = await synthesise(synth_in)
    report_file = Path(f"out/{run_id}/report.md")
    assert report_file.exists()
    content = report_file.read_text(encoding="utf-8")

    # The synthesis report must not contain hallucinated numbers
    assert "999 MW" not in content
    assert len(out.findings) > 0
