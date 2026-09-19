"""Unit tests for BESS footprint sizing, geometry generation, and synthesis."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
from shapely.geometry import shape

from bessible.footprint import (
    DEFAULT_DURATION_H,
    M2_PER_ACRE,
    footprint_polygon,
    reserved_acres,
    reserved_acres_by_duration,
)
from bessible.location.geometry import Site
from bessible.location.models import Coordinates
from bessible.models import (
    Artifact,
    AssessmentRequest,
    CapacityOutput,
    ConfirmedSite,
    DurationCase,
    FinancialOutput,
    GridOutput,
    MarketOutput,
    PlanningOutput,
    Position,
    SiteDecision,
    SiteLandOutput,
    SynthesisInput,
    TitleOutput,
)
from bessible.stages.synthesis import synthesise

if TYPE_CHECKING:
    from pathlib import Path


def test_reserved_acres_proportional_to_energy():
    """Verify 10 MW at 2 h gives 1.0 to 1.5 acres, and doubling duration doubles the range."""
    r2 = reserved_acres(10.0, 2)
    assert r2 == (1.0, 1.5)

    r4 = reserved_acres(10.0, 4)
    assert r4 == (2.0, 3.0)
    assert r4[0] == pytest.approx(2 * r2[0])
    assert r4[1] == pytest.approx(2 * r2[1])

    r8 = reserved_acres(10.0, 8)
    assert r8 == (4.0, 6.0)
    assert r8[0] == pytest.approx(2 * r4[0])
    assert r8[1] == pytest.approx(2 * r4[1])


def test_reserved_acres_defaults_to_4h():
    """Verify reserved_acres uses 4 hours when duration is omitted."""
    assert reserved_acres(10.0) == reserved_acres(10.0, DEFAULT_DURATION_H)


def test_reserved_acres_by_duration():
    """Verify reserved_acres_by_duration returns entries for 2, 4, and 8 hours."""
    res = reserved_acres_by_duration(10.0)
    assert set(res.keys()) == {2, 4, 8}
    assert res[2] == (1.0, 1.5)
    assert res[4] == (2.0, 3.0)
    assert res[8] == (4.0, 6.0)


def test_footprint_polygon_area_in_london():
    """Verify that a 1.0-acre footprint polygon in London measures 1.0 acre within 1%."""
    center = Position(lat=51.5074, lon=-0.1278)  # Central London
    target_acres = 1.0
    geojson = footprint_polygon(center, acres=target_acres, aspect=2.0)

    assert geojson["type"] == "Polygon"
    assert len(geojson["coordinates"]) == 1
    ring = geojson["coordinates"][0]
    assert len(ring) == 5
    assert ring[0] == ring[-1]  # Closed polygon ring

    poly = shape(geojson)
    site = Site(Coordinates(lat=center.lat, lon=center.lon))
    m_poly = site.to_m(poly)
    measured_acres = m_poly.area / M2_PER_ACRE
    error_pct = abs(measured_acres - target_acres) / target_acres * 100

    assert error_pct < 1.0  # Within 1%


def test_site_decision_and_confirmed_site_footprint():
    """Verify SiteDecision accepts footprint_geojson and ConfirmedSite holds it."""
    pos = Position(lat=51.5, lon=-0.1)
    poly = footprint_polygon(pos, acres=2.5)

    decision = SiteDecision(
        confirmed=True,
        position=pos,
        capacity_mw=10.0,
        footprint_geojson=poly,
    )
    assert decision.footprint_geojson == poly

    title = TitleOutput(title_number="BK123456", boundary_geojson={}, area_m2=10000.0)
    site = ConfirmedSite(
        position=pos,
        capacity_mw=10.0,
        boundary=title,
        footprint_geojson=decision.footprint_geojson,
    )
    assert site.footprint_geojson == poly


@pytest.mark.anyio
async def test_synthesis_footprint_finding_and_artifact(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Verify synthesis writes footprint.json and produces a reserved-area finding citing an existing artifact."""
    monkeypatch.chdir(tmp_path)
    run_id = "test-footprint-synthesis"
    req = AssessmentRequest(postcode="RH4 1AD")
    pos = Position(lat=51.23, lon=-0.33)
    title_art = Artifact(
        id=f"title-{run_id[:8]}",
        stage="title",
        claim="Title boundary verified",
        file_path="boundary.geojson",
        confidence=0.95,
        model_used="deterministic",
    )
    title = TitleOutput(title_number="BK123", boundary_geojson={}, area_m2=15000.0, artifacts=[title_art])
    site = ConfirmedSite(position=pos, capacity_mw=10.0, boundary=title)
    cap = CapacityOutput(viable=True, firm_mw=10.0, ceiling_mw=10.0, substation="Test 11kV")
    grid = GridOutput(gate2_queue_position=5, indicative_connection_months=12)
    land = SiteLandOutput(land_use="Industrial")
    market = MarketOutput(revenue_gbp_per_mw_year=80000.0)
    fin = FinancialOutput(
        cases=[
            DurationCase(duration_h=2, capex_gbp=3.9e6, npv_gbp=2.1e6, irr=0.195),
            DurationCase(duration_h=4, capex_gbp=6.7e6, npv_gbp=1.9e6, irr=0.140),
            DurationCase(duration_h=8, capex_gbp=12.3e6, npv_gbp=0.1e6, irr=0.082),
        ],
        recommended_h=4,
    )
    plan = PlanningOutput(consenting_route="LPA Consent")

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
        artifacts=[title_art],
    )

    report_out = await synthesise(synth_in)

    # Verify footprint.json exists and has expected structure
    footprint_file = tmp_path / "out" / run_id / "footprint.json"
    assert footprint_file.exists()
    data = json.loads(footprint_file.read_text(encoding="utf-8"))
    assert data["inputs"]["capacity_mw"] == 10.0
    assert data["inputs"]["duration_h"] == 4
    assert data["range_acres"]["min"] == 2.0
    assert data["range_acres"]["max"] == 3.0
    assert "rule_of_thumb" in data

    # Verify findings include reserved-area finding citing existing artifact
    finding_texts = [f.text for f in report_out.findings]
    assert any("Reserved area requirement: 2.0 to 3.0 acres for 10 MW" in t for t in finding_texts)

    footprint_finding = next(f for f in report_out.findings if "Reserved area requirement" in f.text)
    assert title_art.id in footprint_finding.artifact_ids

    # Verify footprint artifact is in output artifacts
    art_footprint = next(a for a in report_out.artifacts if a.id.startswith("footprint-"))
    assert art_footprint.file_path == "footprint.json"
    assert art_footprint.stage == "synthesis"
