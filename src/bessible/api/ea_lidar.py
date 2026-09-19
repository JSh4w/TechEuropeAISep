"""Environment Agency LIDAR Composite DTM, 1 m resolution (OGC Web Coverage Service 2.0.1).

Dataset: https://environment.data.gov.uk/dataset/13787b9a-26a4-4775-8523-806d13af58fc
Replaces Open-Meteo's 90 m DEM for "is the plot flat enough?": bare-earth heights (buildings and trees
removed) on a ~1 m grid.

Notes (verified live 2026-09):
- No key. ENGLAND only (~99% covered); outside the coverage the server answers HTTP 500
  ``{"message": "Internal server error"}`` rather than an empty raster -> ``WcsError``.
- The response is a GeoTIFF, not JSON: uncompressed big-endian float32, tiled, georeferenced in
  EPSG:4326 when the subset is given in EPSG:4326. ``DtmGrid.from_geotiff`` reads exactly that layout
  with the standard library, so no raster dependency is needed.
- ``scaleFactor`` (0-1] downsamples server-side; a 1 km square at full resolution is ~6 MB.
  ``scalesize`` / ``scaleaxes`` give HTTP 500.
"""

from __future__ import annotations

import math
import struct
from typing import Any, ClassVar, Literal

from pydantic import BaseModel, Field

from .base import ApiRequest, ApiResponse

COVERAGE_ID = "13787b9a-26a4-4775-8523-806d13af58fc__Lidar_Composite_Elevation_DTM_1m"

_EPSG = "http://www.opengis.net/def/crs/EPSG/0/{}"

# ------------------------------------------ 1. Request ------------------------------------------ #


class DtmCoverageRequest(ApiRequest):
    """GET GetCoverage - the DTM raster for a bounding box."""

    URL: ClassVar[str] = "https://environment.data.gov.uk/spatialdata/lidar-composite-digital-terrain-model-dtm-1m/wcs"
    METHOD: ClassVar[str] = "GET"

    service: Literal["WCS"] = "WCS"
    version: Literal["2.0.1"] = "2.0.1"
    request: Literal["GetCoverage"] = "GetCoverage"
    coverage_id: str = Field(default=COVERAGE_ID, serialization_alias="coverageId")
    format: Literal["image/tiff"] = "image/tiff"
    subset: list[str]  # one per axis, e.g. ["Lat(51.23,51.24)", "Long(-0.34,-0.33)"]; sent as repeated params
    subsetting_crs: str = Field(default=_EPSG.format(4326), serialization_alias="subsettingCrs")
    scale_factor: float | None = Field(default=None, serialization_alias="scaleFactor", gt=0, le=1)


# ----------------------------------------- 2. Response ------------------------------------------ #


class WcsError(ApiResponse):
    """HTTP 500 JSON body, which is also what a box outside the LIDAR coverage returns."""

    message: str
    status_code: int = Field(alias="statusCode")
    code: str


# -------------------- 4. Not from the API (helpers, registries, transforms) --------------------- #


def dtm_for_bbox(
    min_lat: float, min_lon: float, max_lat: float, max_lon: float, max_pixels: int = 250
) -> DtmCoverageRequest:
    """Request the DTM for a WGS84 box, downsampled so its longer side is at most `max_pixels`."""
    height_m = (max_lat - min_lat) * 110_540
    width_m = (max_lon - min_lon) * 111_320 * math.cos(math.radians((min_lat + max_lat) / 2))
    scale = min(1.0, max_pixels / max(height_m, width_m, 1.0))
    return DtmCoverageRequest(
        subset=[f"Lat({min_lat},{max_lat})", f"Long({min_lon},{max_lon})"],
        scale_factor=None if scale == 1 else round(scale, 4),
    )


# TIFF / GeoTIFF tag ids
_WIDTH, _HEIGHT, _BITS, _COMPRESSION, _SAMPLE_FORMAT = 256, 257, 258, 259, 339
_STRIP_OFFSETS, _ROWS_PER_STRIP = 273, 278
_TILE_WIDTH, _TILE_HEIGHT, _TILE_OFFSETS = 322, 323, 324
_MODEL_PIXEL_SCALE, _MODEL_TIEPOINT, _MODEL_TRANSFORMATION, _GDAL_NODATA = 33550, 33922, 34264, 42113
_TAG_FORMATS = {1: "B", 2: "c", 3: "H", 4: "I", 5: "II", 11: "f", 12: "d", 16: "Q"}
_INLINE_BYTES = 4  # a tag value this small sits in the directory entry itself, otherwise the entry holds its offset


def _tiff_tags(data: bytes) -> tuple[str, dict[int, tuple[Any, ...]]]:
    """Byte-order prefix and the first image directory of a classic TIFF as {tag: values}."""
    if data[:2] not in {b"MM", b"II"}:
        msg = "not a TIFF"
        raise ValueError(msg)
    e = ">" if data[:2] == b"MM" else "<"
    (ifd,) = struct.unpack_from(e + "I", data, 4)
    (count,) = struct.unpack_from(e + "H", data, ifd)
    tags: dict[int, tuple[Any, ...]] = {}
    for i in range(count):
        tag, kind, n = struct.unpack_from(e + "HHI", data, ifd + 2 + 12 * i)
        fmt = e + _TAG_FORMATS[kind] * n
        pos = ifd + 10 + 12 * i
        if struct.calcsize(fmt) > _INLINE_BYTES:
            (pos,) = struct.unpack_from(e + "I", data, pos)
        tags[tag] = struct.unpack_from(fmt, data, pos)
    return e, tags


def _tiff_rows(data: bytes, e: str, tags: dict[int, tuple[Any, ...]]) -> list[list[float | None]]:
    """Pixel rows of an uncompressed float32 TIFF stored as tiles or strips; no-data cells become None."""
    width, height = tags[_WIDTH][0], tags[_HEIGHT][0]
    if (tags[_BITS][0], tags[_COMPRESSION][0], tags.get(_SAMPLE_FORMAT, (1,))[0]) != (32, 1, 3):
        msg = "expected uncompressed 32-bit float samples"
        raise ValueError(msg)
    nodata = float(b"".join(tags[_GDAL_NODATA]).rstrip(b"\x00")) if _GDAL_NODATA in tags else None
    if _TILE_OFFSETS in tags:  # tiles are padded to the full tile width
        block_w, block_h, offsets = tags[_TILE_WIDTH][0], tags[_TILE_HEIGHT][0], tags[_TILE_OFFSETS]
    else:  # strips are exactly the image width
        block_w, block_h, offsets = width, tags.get(_ROWS_PER_STRIP, (height,))[0], tags[_STRIP_OFFSETS]
    across = -(-width // block_w)
    rows: list[list[float | None]] = [[None] * width for _ in range(height)]
    for b, offset in enumerate(offsets):
        x0, y0 = (b % across) * block_w, (b // across) * block_h
        for y in range(min(block_h, height - y0)):
            values = struct.unpack_from(e + "f" * block_w, data, offset + 4 * block_w * y)
            rows[y0 + y][x0 : x0 + block_w] = [
                None if v == nodata or math.isnan(v) else round(v, 3) for v in values[: width - x0]
            ]
    return rows


def _tiff_georeference(tags: dict[int, tuple[Any, ...]]) -> tuple[float, float, float, float]:
    """(west, north, pixel_lon, pixel_lat) from the GeoTIFF tags."""
    if _MODEL_TRANSFORMATION in tags:  # 4x4 affine
        t = tags[_MODEL_TRANSFORMATION]
        return t[3], t[7], t[0], -t[5]
    (pixel_lon, pixel_lat, _), tie = tags[_MODEL_PIXEL_SCALE], tags[_MODEL_TIEPOINT]
    return tie[3] - tie[0] * pixel_lon, tie[4] + tie[1] * pixel_lat, pixel_lon, pixel_lat


class DtmGrid(BaseModel):
    """A decoded DTM raster (ours, not an API shape: the API returns GeoTIFF bytes).

    Row 0 is the northern edge; ``None`` marks no-data cells.
    """

    width: int
    height: int
    west: float  # lon of the left edge of column 0
    north: float  # lat of the top edge of row 0
    pixel_lon: float  # degrees per column
    pixel_lat: float  # degrees per row (positive)
    rows: list[list[float | None]]  # metres above Ordnance Datum

    @property
    def pixel_m(self) -> tuple[float, float]:
        """Cell size in metres (east-west, north-south)."""
        return self.pixel_lon * 111_320 * math.cos(math.radians(self.north)), self.pixel_lat * 110_540

    def at(self, lat: float, lon: float) -> float | None:
        """Height of the cell containing a point, or None outside the raster / on no-data."""
        col, row = int((lon - self.west) / self.pixel_lon), int((self.north - lat) / self.pixel_lat)
        return self.rows[row][col] if 0 <= row < self.height and 0 <= col < self.width else None

    def centre(self, row: int, col: int) -> tuple[float, float]:
        """(lat, lon) of a cell's centre."""
        return self.north - (row + 0.5) * self.pixel_lat, self.west + (col + 0.5) * self.pixel_lon

    def slope_percent(self, row: int, col: int) -> float | None:
        """Steepest gradient at a cell from its four neighbours, as a percentage (None at edges / no-data)."""
        if not (0 < row < self.height - 1 and 0 < col < self.width - 1):
            return None
        w, e = self.rows[row][col - 1], self.rows[row][col + 1]
        n, s = self.rows[row - 1][col], self.rows[row + 1][col]
        if w is None or e is None or n is None or s is None:
            return None
        dx, dy = self.pixel_m
        return 100 * math.hypot((e - w) / (2 * dx), (n - s) / (2 * dy))

    @classmethod
    def from_geotiff(cls, data: bytes) -> DtmGrid:
        """Decode the service's GeoTIFF (uncompressed float32, tiles or strips, EPSG:4326)."""
        e, tags = _tiff_tags(data)
        west, north, pixel_lon, pixel_lat = _tiff_georeference(tags)
        return cls(
            width=tags[_WIDTH][0],
            height=tags[_HEIGHT][0],
            west=west,
            north=north,
            pixel_lon=pixel_lon,
            pixel_lat=pixel_lat,
            rows=_tiff_rows(data, e, tags),
        )
