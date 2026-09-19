"""Dummy activities for the map session. Replace each body with the real implementation; keep the signatures."""

from __future__ import annotations

import asyncio
import math
from itertools import pairwise

from models import (
    AreaFeedback,
    AreaSuggestion,
    Artifact,
    AssessmentInput,
    EngineInput,
    EngineResult,
    Polygon,
    ValidateInput,
)
from temporalio import activity

M2_PER_MW = 250  # rough BESS footprint incl. spacing; placeholder for the real feasibility model
EARTH_RADIUS_M = 6_371_000


def _square(lat: float, lng: float, half_side_m: float) -> Polygon:
    dlat = math.degrees(half_side_m / EARTH_RADIUS_M)
    dlng = math.degrees(half_side_m / (EARTH_RADIUS_M * math.cos(math.radians(lat))))
    ring = [
        [lng - dlng, lat - dlat],
        [lng + dlng, lat - dlat],
        [lng + dlng, lat + dlat],
        [lng - dlng, lat + dlat],
    ]
    return Polygon(coordinates=[[*ring, ring[0]]])


def _area_m2(poly: Polygon) -> float:
    """Shoelace area on a local equirectangular projection; fine for site-sized polygons."""
    ring = poly.coordinates[0]
    lat0 = math.radians(sum(p[1] for p in ring) / len(ring))
    kx, ky = math.radians(1) * EARTH_RADIUS_M * math.cos(lat0), math.radians(1) * EARTH_RADIUS_M
    xy = [(lng * kx, lat * ky) for lng, lat in ring]
    return abs(sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in pairwise(xy))) / 2


def _inside(point: list[float], poly: Polygon) -> bool:
    """Ray-casting point-in-polygon."""
    x, y = point
    ring = poly.coordinates[0]
    inside = False
    for (x1, y1), (x2, y2) in pairwise(ring):
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


@activity.defn
async def suggest_area(inp: AssessmentInput) -> AreaSuggestion:
    """AI agent proposes where on the plot the battery should go. Dummy: a square sized for the requested MW."""
    await asyncio.sleep(2)  # pretend the agent is thinking
    half_side = math.sqrt(inp.battery_mw * M2_PER_MW * 1.2) / 2
    return AreaSuggestion(
        area=_square(inp.lat, inp.lng, half_side),
        title_boundary=_square(inp.lat, inp.lng, half_side * 3),
        rationale=f"Flat corner of the plot nearest the access road, sized for {inp.battery_mw:g} MW plus 20% spacing.",
        artifacts=[
            Artifact(
                step="suggest_area",
                claim="Title boundary from HM Land Registry INSPIRE polygon",
                source="https://example.com/inspire/AB123456",
                confidence=0.9,
            ),
        ],
    )


@activity.defn
async def validate_area(args: ValidateInput) -> AreaFeedback:  # ruff: ignore[unused-async] async so it runs on the event loop
    """Check a human-edited area against the title boundary and the requested battery size."""
    inp, area, title = args.inp, args.area, args.title_boundary
    ring = area.coordinates[0]
    if len(ring) < 4:  # ruff: ignore[magic-value-comparison] a closed triangle has 4 coordinates
        return AreaFeedback(ok=False, area_m2=0, capacity_mw=0, issues=["Need at least 3 points"])
    m2 = _area_m2(area)
    capacity = m2 / M2_PER_MW
    issues = []
    if not all(_inside(p, title) for p in ring[:-1]):
        issues.append("Area goes outside the title boundary")
    if capacity < inp.battery_mw:
        issues.append(f"Too small: fits ~{capacity:.1f} MW, you asked for {inp.battery_mw:g} MW")
    return AreaFeedback(ok=not issues, area_m2=round(m2), capacity_mw=round(capacity, 1), issues=issues)


@activity.defn
async def run_feasibility(args: EngineInput) -> EngineResult:
    """Planning policy, permissions and battery size: is it possible?"""
    await asyncio.sleep(2)
    return EngineResult(
        score=0.7,
        summary=f"{args.feedback.capacity_mw:g} MW fits; permitted development unlikely, full planning needed",
        artifacts=[
            Artifact(
                step="feasibility",
                claim="Local plan policy EN7 supports storage",
                source="https://example.com/local-plan.pdf",
                confidence=0.6,
            ),
        ],
    )


@activity.defn
async def run_suitability(args: EngineInput) -> EngineResult:
    """Local news and the financial model: is it a good idea?"""
    await asyncio.sleep(2)
    return EngineResult(
        score=0.6,
        summary=f"Mixed local sentiment; payback ~7 years on £{args.inp.budget_gbp:,} at 5% interest",
        artifacts=[
            Artifact(
                step="suitability",
                claim="Local objections to a nearby solar farm in 2025",
                source="https://example.com/news/123",
                confidence=0.5,
            ),
        ],
    )


ALL = [suggest_area, validate_area, run_feasibility, run_suitability]
