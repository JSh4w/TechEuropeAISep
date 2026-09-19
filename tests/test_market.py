"""Unit tests for the market revenue package and assessment stage."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from pydantic import HttpUrl

from bessible.market import load_market_assumptions
from bessible.market.sources import FallbackSource, FixtureSource, RevenueSource, default_sources
from bessible.market.stack import revenue_stack, total
from bessible.market.support import qualifying, support_stream
from bessible.models import (
    AssessmentRequest,
    CapacityOutput,
    ConfirmedSite,
    NodeInput,
    Position,
    TitleOutput,
)
from bessible.stages.market import market_revenue


def test_market_assumptions():
    a = load_market_assumptions()
    assert "capacity_market_derating" in a.entries
    assert "cap_and_floor" in a.entries
    assert "ultra_lds" in a.entries


@pytest.mark.anyio
async def test_revenue_stack_and_derating():
    a = load_market_assumptions()
    sources = default_sources()
    stack = await revenue_stack(20.0, sources, a)

    assert set(stack.keys()) == {2, 4, 8}

    cm_2h = next(s for s in stack[2] if s.stream == "capacity_market")
    cm_4h = next(s for s in stack[4] if s.stream == "capacity_market")
    cm_8h = next(s for s in stack[8] if s.stream == "capacity_market")

    # De-rating factors: 2h is 0.20, 4h is 0.40, 8h is 0.65 with base 60,000
    assert cm_2h.gbp_per_mw_year == pytest.approx(12000.0)
    assert cm_4h.gbp_per_mw_year == pytest.approx(24000.0)
    assert cm_8h.gbp_per_mw_year == pytest.approx(39000.0)

    # Shorter duration earns less Capacity Market revenue
    assert cm_2h.gbp_per_mw_year < cm_4h.gbp_per_mw_year < cm_8h.gbp_per_mw_year

    # Total equals sum of rows
    for rows in stack.values():
        assert total(rows) == sum(r.gbp_per_mw_year for r in rows)


@pytest.mark.anyio
async def test_fallback_source_on_live_failure():
    fixture_src = FixtureSource("capacity_market")
    failing_live = AsyncMock(spec=RevenueSource)
    failing_live.name = "live_cm"
    failing_live.fetch.side_effect = ConnectionError("Live endpoint timeout")

    fallback = FallbackSource(live=failing_live, fixture=fixture_src)
    val = await fallback.fetch(4)

    assert val.stream == "capacity_market"
    assert val.cached is True
    assert val.source_url == HttpUrl("https://www.emrdeliverybody.com/")


def test_long_duration_support_qualifying():
    a = load_market_assumptions()

    # 2h 20MW qualifies for neither
    assert qualifying(2, 20.0, a) == []
    # 4h 120MW qualifies for neither (needs min 8h for cap_and_floor)
    assert qualifying(4, 120.0, a) == []
    # 8h 20MW does not qualify for cap_and_floor (min 100MW required)
    assert qualifying(8, 20.0, a) == []
    # 8h 100MW qualifies for cap_and_floor
    assert qualifying(8, 100.0, a) == ["cap_and_floor"]
    # 24h 100MW qualifies for both cap_and_floor and ultra_lds
    assert qualifying(24, 100.0, a) == ["cap_and_floor", "ultra_lds"]

    stream = support_stream("cap_and_floor", a)
    assert stream.stream == "cap_and_floor"
    assert stream.scheme == "Ofgem LDES cap and floor"
    assert stream.gbp_per_mw_year == 20000.0


@pytest.mark.anyio
async def test_market_revenue_stage():
    req = AssessmentRequest(postcode="RH4 1AD")
    cap = CapacityOutput(viable=True, firm_mw=10.0, ceiling_mw=20.0, recommended_mw=15.0)
    title = TitleOutput(
        title_number="SY12345",
        area_m2=5000.0,
        boundary_geojson={"type": "Polygon", "coordinates": []},
    )
    site = ConfirmedSite(position=Position(lat=51.23, lon=-0.33), capacity_mw=15.0, boundary=title)
    inp = NodeInput(run_id="run-mkt-test", request=req, site=site, capacity=cap)

    out = await market_revenue(inp)
    assert out.revenue_gbp_per_mw_year > 0
    assert out.by_duration is not None
    assert len(out.by_duration) == 3
    assert "capacity_market" in out.streams
    assert "balancing_ancillary" in out.streams
    assert "wholesale" in out.streams

    # Every stream has an artifact with source link
    assert len(out.artifacts) >= 3
    for art in out.artifacts:
        assert art.source_url is not None
        assert art.stage == "market"
