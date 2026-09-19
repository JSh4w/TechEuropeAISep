from __future__ import annotations

from pathlib import Path

import pytest

from bessible.models import (
    AssessmentRequest,
    ConfirmedSite,
    FinancialInput,
    LocationInput,
    NodeInput,
    PlanningInput,
    Position,
    SynthesisInput,
    TitleInput,
)
from bessible.stages.capacity import propose_capacity
from bessible.stages.financial import financial_model
from bessible.stages.grid import grid_connection
from bessible.stages.location import resolve_location
from bessible.stages.market import market_revenue
from bessible.stages.planning import regulatory_planning
from bessible.stages.site_land import site_land
from bessible.stages.synthesis import synthesise
from bessible.stages.title import find_title_boundaries


@pytest.mark.anyio
async def test_location_and_capacity_stages():
    run_id = "test-run-stages"
    req = AssessmentRequest(postcode="RH4 1AD")
    loc_in = LocationInput(run_id=run_id, request=req)
    loc_out = await resolve_location(loc_in)

    assert loc_out.postcode == "RH4 1AD"
    assert loc_out.position.lat == pytest.approx(51.2329, abs=1e-3)
    assert len(loc_out.artifacts) == 1

    from bessible.models import CapacityInput

    cap_in = CapacityInput(run_id=run_id, request=req, location=loc_out)
    cap_out = await propose_capacity(cap_in)
    assert cap_out.viable is True
    assert cap_out.substation == "Dorking Town 11kV"
    assert cap_out.firm_mw == 8.0  # import 14.7 MW, capped by the 11 kV limit
    assert cap_out.ceiling_mw == 8.0
    assert cap_out.binding_direction == "import"


@pytest.mark.anyio
async def test_capacity_below_floor_flexible():
    from bessible.models import CapacityInput

    run_id = "test-below-floor"
    # Without flexible connection -> not viable, below 5 MW floor
    req_firm = AssessmentRequest(postcode="RH3 7EZ", flexible_connection=False)
    loc = await resolve_location(LocationInput(run_id=run_id, request=req_firm))
    cap_firm = await propose_capacity(CapacityInput(run_id=run_id, request=req_firm, location=loc))
    assert cap_firm.viable is False
    assert cap_firm.firm_mw == 2.2
    assert "below the 5 MW floor" in (cap_firm.message or "")

    # With flexible connection -> viable at ceiling (6.5 MW)
    req_flex = AssessmentRequest(postcode="RH3 7EZ", flexible_connection=True)
    cap_flex = await propose_capacity(CapacityInput(run_id=run_id, request=req_flex, location=loc))
    assert cap_flex.viable is True
    assert cap_flex.ceiling_mw == pytest.approx(6.5)
    assert cap_flex.substation == "Betchworth 11kV"


@pytest.mark.anyio
async def test_capacity_out_of_area():
    from bessible.models import CapacityInput, LocationOutput

    manchester = LocationOutput(postcode="M1 1AE", position=Position(lat=53.4808, lon=-2.2426))
    req = AssessmentRequest(postcode="M1 1AE")
    cap = await propose_capacity(CapacityInput(run_id="ooa", request=req, location=manchester))
    assert cap.out_of_area is True
    assert cap.viable is False
    assert cap.message is not None


@pytest.mark.anyio
async def test_title_and_analysis_stages():
    run_id = "test-analysis-stages"
    req = AssessmentRequest(postcode="RH4 1AD")
    loc = await resolve_location(LocationInput(run_id=run_id, request=req))

    from bessible.models import CapacityInput

    cap = await propose_capacity(CapacityInput(run_id=run_id, request=req, location=loc))
    title = await find_title_boundaries(TitleInput(run_id=run_id, request=req, location=loc, capacity=cap))
    assert title.title_number == "BK123456"

    boundary_file = Path(f"out/{run_id}/boundary.geojson")
    assert boundary_file.exists()

    site = ConfirmedSite(position=Position(lat=51.6, lon=-1.2), capacity_mw=12.0, boundary=title)
    node_in = NodeInput(run_id=run_id, request=req, site=site, capacity=cap)

    grid = await grid_connection(node_in)
    land = await site_land(node_in)
    market = await market_revenue(node_in)

    fin = await financial_model(
        FinancialInput(run_id=run_id, request=req, site=site, capacity=cap, grid=grid, market=market)
    )
    plan = await regulatory_planning(
        PlanningInput(run_id=run_id, request=req, site=site, capacity=cap, grid=grid, site_land=land)
    )

    assert len(fin.cases) == 3
    assert len(plan.risks) > 0

    all_arts = (
        loc.artifacts
        + cap.artifacts
        + title.artifacts
        + grid.artifacts
        + land.artifacts
        + market.artifacts
        + fin.artifacts
        + plan.artifacts
    )
    synth = await synthesise(
        SynthesisInput(
            run_id=run_id,
            request=req,
            site=site,
            capacity=cap,
            grid=grid,
            site_land=land,
            market=market,
            financial=fin,
            planning=plan,
            artifacts=all_arts,
        )
    )

    assert synth.verdict == "go"
    assert len(synth.findings) > 0
    report_file = Path(f"out/{run_id}/report.md")
    assert report_file.exists()
