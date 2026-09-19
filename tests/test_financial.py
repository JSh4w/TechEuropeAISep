"""Unit tests for the financial model package and assessment stage."""

from __future__ import annotations

import pytest

from bessible.assumptions import AssumptionSet, MissingAssumption
from bessible.finance import load_finance_assumptions
from bessible.finance.cost import cost
from bessible.finance.curtailment import curtailment_pct, load_demand_profile, load_duration_curve
from bessible.finance.returns import returns
from bessible.models import (
    AssessmentRequest,
    CapacityOutput,
    ConfirmedSite,
    FinancialInput,
    GridOutput,
    MarketOutput,
    Position,
    SiteLandOutput,
    TitleOutput,
)
from bessible.stages.financial import financial_model


def test_missing_assumption():
    empty_set = AssumptionSet(entries={})
    with pytest.raises(MissingAssumption) as exc_info:
        empty_set.number("battery_gbp_per_mwh")
    assert "battery_gbp_per_mwh" in str(exc_info.value)


def test_cost_scaling_and_connection():
    a = load_finance_assumptions()

    # CAPEX grows with duration
    c2 = cost(2, 20.0, 1.0, crossings=False, a=a)
    c4 = cost(4, 20.0, 1.0, crossings=False, a=a)
    c8 = cost(8, 20.0, 1.0, crossings=False, a=a)
    assert c2.capex_gbp < c4.capex_gbp < c8.capex_gbp

    # Connection cost for 1 km
    assert c2.connection_gbp == (500000.0, 700000.0)

    # Connection cost for 3 km
    c3km = cost(4, 20.0, 3.0, crossings=False, a=a)
    assert c3km.connection_gbp == (1500000.0, 2100000.0)

    # Crossing uplift (25%)
    c_cross = cost(4, 20.0, 1.0, crossings=True, a=a)
    assert c_cross.connection_gbp == (625000.0, 875000.0)
    assert c_cross.crossing_uplift_applied is True


def test_otcf_thresholds():
    a = load_finance_assumptions()

    # Default in finance.json is 30% (between 25% and 50% -> inactive)
    c = cost(4, 20.0, 1.0, crossings=False, a=a)
    assert c.otcf_gbp is None
    assert "inactive" in c.otcf_state

    # Over 50% -> active
    a_high = load_finance_assumptions()
    a_high.entries["oversubscription_pct"].value = 60
    c_high = cost(4, 20.0, 1.0, crossings=False, a=a_high)
    assert c_high.otcf_gbp == (60000.0, 500000.0)
    assert "active" in c_high.otcf_state
    assert "proposed" in c_high.otcf_state

    # Below 25% -> inactive
    a_low = load_finance_assumptions()
    a_low.entries["oversubscription_pct"].value = 20
    c_low = cost(4, 20.0, 1.0, crossings=False, a=a_low)
    assert c_low.otcf_gbp is None
    assert "inactive" in c_low.otcf_state


def test_curtailment_logic():
    a = load_finance_assumptions()
    profile = load_demand_profile()
    max_mw = a.number("substation_max_demand_mw")
    min_mw = a.number("substation_min_demand_mw")
    curve = load_duration_curve(max_mw, min_mw, profile.values)

    assert max(curve) == pytest.approx(max_mw)
    assert min(curve) == pytest.approx(min_mw)

    # Within firm headroom: 0% curtailment
    curt_firm = curtailment_pct(10.0, 10.0, 25.0, curve, 4, max_mw=max_mw, min_mw=min_mw)
    assert curt_firm == 0.0

    # Above firm headroom: positive curtailment
    curt_flex = curtailment_pct(20.0, 10.0, 25.0, curve, 4, max_mw=max_mw, min_mw=min_mw)
    assert curt_flex > 0.0


def test_returns_and_budget():
    a = load_finance_assumptions()
    c4 = cost(4, 10.0, 1.0, crossings=False, a=a)

    # Known repeatable calculation
    r1 = returns(c4, 94000.0, 5.0, 10.0, a, budget_gbp=10_000_000.0)
    r2 = returns(c4, 94000.0, 5.0, 10.0, a, budget_gbp=10_000_000.0)
    assert r1.capex_gbp == r2.capex_gbp
    assert r1.npv_gbp == r2.npv_gbp
    assert r1.irr == r2.irr
    assert r1.over_budget is True  # capex > 10m

    # Budget check flags over budget appropriately
    r_high_budget = returns(c4, 94000.0, 5.0, 10.0, a, budget_gbp=50_000_000.0)
    assert r_high_budget.over_budget is False


@pytest.mark.anyio
async def test_financial_stage_end_to_end():
    req = AssessmentRequest(postcode="RH4 1AD", budget_gbp=15_000_000.0)
    cap = CapacityOutput(viable=True, firm_mw=8.0, ceiling_mw=16.0, recommended_mw=12.0, distance_km=1.5)
    title = TitleOutput(
        title_number="SY12345",
        area_m2=5000.0,
        boundary_geojson={"type": "Polygon", "coordinates": []},
    )
    site = ConfirmedSite(position=Position(lat=51.23, lon=-0.33), capacity_mw=12.0, boundary=title)
    grid = GridOutput()
    land = SiteLandOutput(
        land_use="Industrial",
        constraints=["Railway crossing required for 33kV cable route", "Low flood risk"],
    )
    market = MarketOutput(
        revenue_gbp_per_mw_year=94000.0,
        streams={"wholesale": 45000.0, "capacity_market": 24000.0, "balancing_ancillary": 25000.0},
    )

    inp = FinancialInput(
        run_id="run-fin-test",
        request=req,
        site=site,
        capacity=cap,
        grid=grid,
        market=market,
        site_land=land,
    )

    out = await financial_model(inp)
    assert len(out.cases) == 3
    assert [c.duration_h for c in out.cases] == [2, 4, 8]

    # Crossing uplift applied because of railway crossing constraint
    cost_art = next(a for a in out.artifacts if "cost" in a.id)
    assert "crossing uplift of 25% applied" in cost_art.claim
    assert "interest rate 6.5%" in cost_art.claim

    # Curtailment artifact states demand profile and documented assumption
    curt_art = next(a for a in out.artifacts if "curtailment" in a.id)
    assert "documented assumption, not measured data" in curt_art.claim
    assert "Demand profile:" in curt_art.claim

    # Returns artifact documents returns and flags cases over budget if applicable
    ret_art = next(a for a in out.artifacts if "returns" in a.id)
    assert "25-year returns:" in ret_art.claim
