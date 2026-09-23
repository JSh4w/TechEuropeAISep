from __future__ import annotations

import pytest

from bessible.cable_route import with_cable_route
from bessible.models import (
    AssessmentRequest,
    CableRoute,
    CapacityOutput,
    ConfirmedSite,
    FinancialInput,
    GridOutput,
    MarketOutput,
    Position,
    TitleOutput,
)
from bessible.stages.capacity import propose
from bessible.stages.financial import financial_model
from bessible.ukpn.snapshot import get_snapshot

SITE = Position(lat=51.2329, lon=-0.3302)
SUBSTATION = Position(lat=51.2375, lon=-0.3265)


def capacity(**update: object) -> CapacityOutput:
    base = CapacityOutput(
        viable=True,
        substation="Dorking Town 11kV",
        firm_mw=8.0,
        ceiling_mw=8.0,
        recommended_mw=8.0,
        distance_km=0.57,
        substation_position=SUBSTATION,
    )
    return base.model_copy(update=update)


def test_route_is_the_straight_line_priced_with_the_detour_factor():
    out = with_cable_route(SITE, capacity(), "run-route")
    route = out.route
    assert route is not None
    assert route.path == [SITE, SUBSTATION]
    assert route.straight_km == pytest.approx(0.57, abs=0.01)
    assert route.detour_factor == 1.5
    assert route.distance_km == round(route.straight_km * 1.5, 2)
    art = out.artifacts[-1]
    assert art.model_used == "straight-line"
    assert art.file_path == "data/assumptions/finance.json"
    assert "x1.5 detour factor" in art.claim


def test_no_substation_leaves_output_unchanged():
    out = capacity(substation_position=None)
    assert with_cable_route(SITE, out, "run-route") == out


def test_propose_returns_substation_position():
    out = propose(SITE, get_snapshot(), "run-route", flexible=False)
    assert out.substation is not None
    assert out.substation_position is not None


@pytest.mark.anyio
async def test_financial_model_prices_cable_on_route():
    road = CableRoute(distance_km=3.0, straight_km=2.0, detour_factor=1.5, path=[SITE, SUBSTATION])
    inp = FinancialInput(
        run_id="run-fin-route",
        request=AssessmentRequest(postcode="RH4 1AD"),
        site=ConfirmedSite(
            position=SITE,
            capacity_mw=8.0,
            boundary=TitleOutput(title_number="SY12345", area_m2=5000.0, boundary_geojson={"type": "Polygon"}),
        ),
        capacity=capacity(route=road),
        grid=GridOutput(),
        market=MarketOutput(revenue_gbp_per_mw_year=94000.0),
    )
    cost_art = next(a for a in (await financial_model(inp)).artifacts if "cost" in a.id)
    assert "over 3.00 km, 2 km straight line x1.5 detour" in cost_art.claim
