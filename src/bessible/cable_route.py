"""Cable run from the site to the serving substation: the straight line, priced with a detour factor.

A street route drawn at screening stage misleads more than it helps: one-way systems, footpaths and barriers such as
railways make the shortest street route wander, while the DNO may cross land under a wayleave. So the map shows the
straight line, and the cable is priced on that line times a standard detour factor for the route it would really take.

Runs after the capacity proposal and does no I/O. It never fails a capacity check.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bessible.api.geo import distance_km
from bessible.assumptions import ASSUMPTIONS_DIR
from bessible.finance import load_finance_assumptions
from bessible.models import Artifact, CableRoute, Position

if TYPE_CHECKING:
    from bessible.models import CapacityOutput

FINANCE_ASSUMPTIONS = ASSUMPTIONS_DIR / "finance.json"  # holds `cable_detour_factor`


def straight_line(site: Position, substation: Position) -> CableRoute:
    """The straight line to the substation, with its priced length."""
    factor = load_finance_assumptions().number("cable_detour_factor")
    straight = round(distance_km(site.lat, site.lon, substation.lat, substation.lon), 2)
    return CableRoute(
        distance_km=round(straight * factor, 2), straight_km=straight, detour_factor=factor, path=[site, substation]
    )


def with_cable_route(site: Position, out: CapacityOutput, run_id: str) -> CapacityOutput:
    """`out` with its cable run and an artifact stating the assumption. Unchanged when there is no substation."""
    if out.substation_position is None:
        return out
    route = straight_line(site, out.substation_position)
    name = out.substation or "the serving substation"
    art = Artifact(
        id=f"capacity-cable-route-{run_id[:8]}",
        stage="capacity",
        claim=(
            f"Cable run to {name}: {route.straight_km:g} km straight line, priced as {route.distance_km:g} km "
            f"(x{route.detour_factor:g} detour factor for roads and field edges). The DNO designs the actual route"
        ),
        file_path=str(FINANCE_ASSUMPTIONS.relative_to(ASSUMPTIONS_DIR.parents[1])),
        confidence=0.6,
        model_used="straight-line",
    )
    return out.model_copy(update={"route": route, "artifacts": [*out.artifacts, art]})
