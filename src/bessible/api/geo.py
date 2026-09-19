"""Client-side geography for portals that have no spatial query (not part of any API)."""

from __future__ import annotations

import math
from operator import itemgetter
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable


def distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km."""
    a = (
        math.sin(math.radians(lat2 - lat1) / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    )
    return 6371 * 2 * math.asin(math.sqrt(a))


def nearest[T](
    records: list[T],
    lat: float,
    lon: float,
    max_km: float,
    position: Callable[[T], tuple[float | None, float | None]],
) -> list[tuple[float, T]]:
    """(km, record) for the records within `max_km` of a WGS84 point, nearest first.

    `position` returns a record's (lat, lon); records without one are skipped.
    """
    near = [
        (distance_km(lat, lon, p[0], p[1]), r)
        for r in records
        if (p := position(r))[0] is not None and p[1] is not None
    ]
    return sorted(((d, r) for d, r in near if d <= max_km), key=itemgetter(0))
