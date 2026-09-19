"""Curtailment estimate from a synthesised load duration curve.

This is a documented assumption, not measured data. Method: the battery discharges in the top
`duration_h` hours of each day and charges in the bottom `duration_h` hours. A discharge hour is
constrained when demand is within `firm_mw` of the substation maximum (peak side). A charge hour is
constrained when demand is within `firm_mw` of the minimum (trough side). Curtailment is the share of
dispatch hours that are constrained, scaled by how far capacity sits between firm and ceiling.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import NamedTuple

from bessible.assumptions import ASSUMPTIONS_DIR

HOURS_PER_YEAR = 8760
DAYS_PER_YEAR = 365
HOURS_PER_DAY = 24
MONTH_DAYS = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)


class DemandProfile(NamedTuple):
    """A normalised year of hourly demand shape and where it came from."""

    values: list[float]
    source: str
    date: str


def load_demand_profile(path: Path = ASSUMPTIONS_DIR / "demand_profile.json") -> DemandProfile:
    """Expand the hourly and monthly shape in `demand_profile.json` to 8760 values."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    hourly: list[float] = raw["hourly"]
    monthly: list[float] = raw["monthly"]
    values = [
        hourly[h] * monthly[month] for month, days in enumerate(MONTH_DAYS) for _ in range(days) for h in range(24)
    ]
    return DemandProfile(values=values, source=raw["source"], date=raw["date"])


def load_duration_curve(max_mw: float, min_mw: float, profile: list[float]) -> list[float]:
    """Scale a profile so its highest value is `max_mw` and its lowest is `min_mw`. Keeps time order."""
    high, low = max(profile), min(profile)
    if high == low:
        msg = "Demand profile must not be flat"
        raise ValueError(msg)
    return [min_mw + (v - low) / (high - low) * (max_mw - min_mw) for v in profile]


def curtailment_pct(  # noqa: PLR0913, PLR0917
    capacity_mw: float,
    firm_mw: float,
    ceiling_mw: float,
    curve: list[float],
    duration_h: int,
    *,
    max_mw: float | None = None,
    min_mw: float | None = None,
) -> float:
    """Return curtailment as a percentage (0 to 100). Zero at or below firm capacity."""
    if capacity_mw <= firm_mw or ceiling_mw <= firm_mw:
        return 0.0
    peak = max(curve) if max_mw is None else max_mw
    trough = min(curve) if min_mw is None else min_mw

    dispatch = constrained = 0
    for day in range(len(curve) // HOURS_PER_DAY):
        start = day * HOURS_PER_DAY
        hours = sorted(range(start, start + HOURS_PER_DAY), key=curve.__getitem__)
        for t in hours[-duration_h:]:  # discharge at peak
            dispatch += 1
            constrained += curve[t] > peak - firm_mw
        for t in hours[:duration_h]:  # charge at trough
            dispatch += 1
            constrained += curve[t] < trough + firm_mw
    overlap = constrained / dispatch if dispatch else 0.0
    scale = min(1.0, (capacity_mw - firm_mw) / (ceiling_mw - firm_mw))
    return overlap * scale * 100
