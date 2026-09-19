"""Environment Agency Flood Map for Planning: Flood Zones 2/3 (GeoServer WFS).

No API key. Open Government Licence v3.
(The real-time flood-monitoring API - warnings, areas, stations - is operational data, not a planning
constraint, so it is deliberately not modelled.)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, ClassVar, Literal

from pydantic import Field

from .base import ApiRequest, ApiResponse

_FZ_TYPENAME = "dataset-04532375-a198-476e-985e-0579a0a11b47:Flood_Zones_2_3_Rivers_and_Sea"


# ------------------------------------------ 1. Request ------------------------------------------ #


class FloodZoneRequest(ApiRequest):
    """WFS 2.0 GetFeature on EA "Flood Map for Planning - Flood Zones" (GeoServer).

    Capabilities: {URL}?service=WFS&request=GetCapabilities
    Build with `flood_zone_at_point(lat, lon)`; zero features => Flood Zone 1.
    Native CRS EPSG:27700; geometry column is `shape`.
    """

    URL: ClassVar[str] = "https://environment.data.gov.uk/spatialdata/flood-map-for-planning-flood-zones/wfs"
    METHOD: ClassVar[str] = "GET"

    service: Literal["WFS"] = "WFS"
    version: Literal["2.0.0"] = "2.0.0"
    request: Literal["GetFeature"] = "GetFeature"
    type_names: str = Field(default=_FZ_TYPENAME, alias="typeNames")
    output_format: Literal["application/json"] = Field(default="application/json", alias="outputFormat")
    count: int | None = 20
    # Omitting `shape` returns geometry: null (polygons are large). None => all properties.
    property_name: str | None = Field(default="origin,flood_zone,flood_source", alias="propertyName")
    # ECQL. EWKT points are lon-lat order: INTERSECTS(shape,SRID=4326;POINT(lon lat))
    cql_filter: str | None = None


# ----------------------------------------- 2. Response ------------------------------------------ #


class FloodZoneResponse(ApiResponse):
    """GeoJSON FeatureCollection returned by the Flood Zones WFS."""

    type: Literal["FeatureCollection"]
    features: list[FloodZoneFeature]
    total_features: int | None = Field(default=None, alias="totalFeatures")
    number_matched: int | None = Field(default=None, alias="numberMatched")
    number_returned: int = Field(alias="numberReturned")
    time_stamp: datetime | None = Field(default=None, alias="timeStamp")
    crs: dict[str, Any] | None = None


# ------------------------------------ 3. Response sub-models ------------------------------------ #


class FloodZoneProperties(ApiResponse):
    """Attributes of one flood zone polygon."""

    origin: str | None = None  # seen: modelled | recorded | modelled and recorded
    flood_zone: Literal["FZ2", "FZ3"] | None = None
    flood_source: str | None = None  # seen: river | river and sea


class FloodZoneFeature(ApiResponse):
    """GeoJSON feature for one flood zone polygon."""

    type: Literal["Feature"]
    id: str
    geometry: dict[str, Any] | None = None  # null unless `shape` is requested
    properties: FloodZoneProperties
    bbox: list[float] | None = None  # EPSG:27700 [minE, minN, maxE, maxN]


# -------------------- 4. Not from the API (helpers, registries, transforms) --------------------- #


def flood_zone_at_point(lat: float, lon: float, buffer_m: float | None = None) -> FloodZoneRequest:
    """Request the zones containing a WGS84 point, or within `buffer_m` metres of it."""
    point = f"SRID=4326;POINT({lon} {lat})"
    if buffer_m is None:
        return FloodZoneRequest(cql_filter=f"INTERSECTS(shape,{point})")
    return FloodZoneRequest(cql_filter=f"DWITHIN(shape,{point},{buffer_m},meters)")
