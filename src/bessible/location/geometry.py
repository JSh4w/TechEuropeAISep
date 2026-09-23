"""Measuring things against the site: a local metric frame around it, then plain shapely.

Shapely is planar, so WGS84 geometry is first projected to metres on an equirectangular frame centred on the
site. Over the few kilometres we look at, that is accurate to well under 1 %.
"""

from __future__ import annotations

import json
import math
from typing import TYPE_CHECKING, Any

import numpy as np
import shapely
from shapely.geometry import Point, mapping, shape
from shapely.ops import unary_union

from .models import Coordinates, Geometry

if TYPE_CHECKING:
    from numpy.typing import NDArray
    from shapely.geometry.base import BaseGeometry

M_PER_DEG_LAT = 110_540.0
M_PER_DEG_LON_EQUATOR = 111_320.0


def from_geojson(geometry: Geometry | dict[str, Any]) -> BaseGeometry:
    """A shapely geometry (still in degrees) from GeoJSON; 3D coordinates are flattened."""
    data = geometry.model_dump() if isinstance(geometry, Geometry) else geometry
    return _single_kind(shapely.force_2d(shapely.make_valid(shape(data))))


def _single_kind(geom: BaseGeometry) -> BaseGeometry:
    """Repairing a polygon can leave a GeometryCollection (polygon + stray lines): keep its highest dimension."""
    if geom.geom_type != "GeometryCollection":
        return geom
    parts = list(getattr(geom, "geoms", []))
    top = max((p.area > 0, p.length > 0) for p in parts) if parts else (False, False)
    return unary_union([p for p in parts if (p.area > 0, p.length > 0) == top])


def to_geometry(geom: BaseGeometry) -> Geometry:
    """GeoJSON model of a shapely geometry in degrees, rounded to ~0.1 m."""
    rounded = _single_kind(shapely.set_precision(geom, 1e-6))  # snapping to the grid can split a geometry too
    return Geometry.model_validate(json.loads(json.dumps(mapping(geom if rounded.is_empty else rounded))))


class Site:
    """The area under analysis (title polygon, or just the point) and a metric frame around it."""

    def __init__(self, coords: Coordinates, boundary: BaseGeometry | None = None) -> None:
        """`boundary` is the title polygon in degrees; without one the site is the point itself."""
        self.coords = coords
        self.boundary = boundary
        origin = boundary.centroid if boundary is not None else Point(coords.lon, coords.lat)
        self._lon0, self._lat0 = origin.x, origin.y
        self._kx = M_PER_DEG_LON_EQUATOR * math.cos(math.radians(self._lat0))
        self.shape_m: BaseGeometry = self.to_m(boundary if boundary is not None else origin)

    def to_m(self, geom: BaseGeometry) -> BaseGeometry:
        """Project a geometry in degrees onto the site's metric frame."""
        return shapely.transform(geom, self._project)

    def _project(self, xy: NDArray[np.float64]) -> NDArray[np.float64]:
        return np.column_stack(((xy[:, 0] - self._lon0) * self._kx, (xy[:, 1] - self._lat0) * M_PER_DEG_LAT))

    def to_deg(self, geom: BaseGeometry) -> BaseGeometry:
        """Inverse of `to_m`: a geometry in the site's metric frame back to degrees."""
        return shapely.transform(
            geom, lambda xy: np.column_stack((xy[:, 0] / self._kx + self._lon0, xy[:, 1] / M_PER_DEG_LAT + self._lat0))
        )

    @property
    def bbox(self) -> tuple[float, float, float, float]:
        """(min_lon, min_lat, max_lon, max_lat) of the site."""
        if self.boundary is None:
            return self.coords.lon, self.coords.lat, self.coords.lon, self.coords.lat
        min_lon, min_lat, max_lon, max_lat = self.boundary.bounds
        return min_lon, min_lat, max_lon, max_lat

    def bbox_with_margin(self, margin_m: float) -> tuple[float, float, float, float]:
        """The site's box grown by `margin_m` on every side."""
        min_lon, min_lat, max_lon, max_lat = self.bbox
        dlat, dlon = margin_m / M_PER_DEG_LAT, margin_m / self._kx
        return min_lon - dlon, min_lat - dlat, max_lon + dlon, max_lat + dlat

    def buffered_wkt(self, margin_m: float, tolerance_m: float = 2.0) -> str:
        """WKT (degrees) of the site grown by `margin_m` and simplified, short enough for a query string."""
        grown = self.shape_m.buffer(margin_m, quad_segs=4).simplify(max(tolerance_m, margin_m / 20))
        back = shapely.transform(
            grown, lambda xy: np.column_stack((xy[:, 0] / self._kx + self._lon0, xy[:, 1] / M_PER_DEG_LAT + self._lat0))
        )
        return str(shapely.set_precision(back, 1e-6).wkt)

    def measure(self, geom: BaseGeometry) -> tuple[bool, float | None, float]:
        """(on_site, overlap_pct, distance_m) of a geometry in degrees, against the site.

        `overlap_pct` is the share of the title it covers; None when the site is only a point.
        """
        other = self.to_m(geom)
        distance = float(self.shape_m.distance(other))
        on_site = distance == 0
        if self.boundary is None or self.shape_m.area == 0:
            return on_site, None, round(distance, 1)
        overlap = 100 * self.shape_m.intersection(other).area / self.shape_m.area if on_site else 0.0
        return on_site, round(overlap, 1), round(distance, 1)

    def distance_km(self, lat: float, lon: float) -> float:
        """Distance from the site to a WGS84 point, km."""
        return round(float(self.shape_m.distance(self.to_m(Point(lon, lat)))) / 1000, 2)

    def contains(self, lons: NDArray[np.floating[Any]], lats: NDArray[np.floating[Any]]) -> NDArray[np.bool_]:
        """Which WGS84 points fall inside the title (all False without one)."""
        if self.boundary is None:
            return np.zeros(len(lons), dtype=bool)
        return np.asarray(shapely.contains_xy(self.boundary, lons, lats), dtype=bool)
