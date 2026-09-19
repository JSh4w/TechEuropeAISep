"""BESS footprint and reserved land area sizing calculations."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any

from bessible.location.geometry import M_PER_DEG_LAT, M_PER_DEG_LON_EQUATOR

if TYPE_CHECKING:
    from bessible.models import Position

ACRES_PER_MWH: tuple[float, float] = (0.05, 0.075)
M2_PER_ACRE: float = 4046.8564224
DEFAULT_DURATION_H: int = 4
STANDARD_DURATIONS: tuple[int, ...] = (2, 4, 8)


def reserved_acres(capacity_mw: float, duration_h: int = DEFAULT_DURATION_H) -> tuple[float, float]:
    """Calculate the planning-grade reserved area range in acres for a given capacity and duration."""
    if capacity_mw < 0:
        msg = f"capacity_mw must be non-negative (got {capacity_mw})"
        raise ValueError(msg)
    if duration_h < 0:
        msg = f"duration_h must be non-negative (got {duration_h})"
        raise ValueError(msg)
    energy_mwh = capacity_mw * duration_h
    return (
        round(energy_mwh * ACRES_PER_MWH[0], 4),
        round(energy_mwh * ACRES_PER_MWH[1], 4),
    )


def reserved_acres_by_duration(capacity_mw: float) -> dict[int, tuple[float, float]]:
    """Return reserved area ranges in acres across standard storage durations (2, 4, and 8 hours)."""
    return {d: reserved_acres(capacity_mw, d) for d in STANDARD_DURATIONS}


def footprint_polygon(center: Position, acres: float, aspect: float = 2.0) -> dict[str, Any]:
    """Generate a GeoJSON rectangular polygon representing a footprint of given acreage centred on position.

    The rectangle is computed in a local metric frame (equirectangular approximation around center.lat)
    with the given aspect ratio (width / height) before converting corners back to WGS84 coordinates.
    """
    if acres <= 0:
        msg = f"acres must be positive (got {acres})"
        raise ValueError(msg)
    if aspect <= 0:
        msg = f"aspect must be positive (got {aspect})"
        raise ValueError(msg)

    area_m2 = acres * M2_PER_ACRE
    height = math.sqrt(area_m2 / aspect)
    width = height * aspect
    dx = width / 2.0
    dy = height / 2.0

    lat = center.lat
    lon = center.lon

    cos_lat = math.cos(math.radians(lat))
    kx = M_PER_DEG_LON_EQUATOR * max(cos_lat, 1e-6)
    ky = M_PER_DEG_LAT

    dlon = dx / kx
    dlat = dy / ky

    coords = [
        [lon - dlon, lat - dlat],
        [lon + dlon, lat - dlat],
        [lon + dlon, lat + dlat],
        [lon - dlon, lat + dlat],
        [lon - dlon, lat - dlat],
    ]
    return {
        "type": "Polygon",
        "coordinates": [coords],
    }
