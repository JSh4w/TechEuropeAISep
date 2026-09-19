"""OpenStreetMap Nominatim reverse geocoding.

Docs: https://nominatim.org/release-docs/latest/api/Reverse/
Output: https://nominatim.org/release-docs/latest/api/Output/
Usage policy (public server): send an identifying User-Agent, max 1 request/second.
"""

from __future__ import annotations

from typing import Any, ClassVar, Literal

from pydantic import ConfigDict, Field, field_serializer

from .base import ApiRequest, ApiResponse

Flag = Literal[0, 1]

Layer = Literal["address", "poi", "railway", "natural", "manmade"]


# ------------------------------------------ 1. Request ------------------------------------------ #


class ReverseRequest(ApiRequest):
    """GET https://nominatim.openstreetmap.org/reverse — reverse geocode a coordinate.

    Docs: https://nominatim.org/release-docs/latest/api/Reverse/
    Response models below describe format=jsonv2 only.
    """

    URL: ClassVar[str] = "https://nominatim.openstreetmap.org/reverse"
    METHOD: ClassVar[str] = "GET"

    lat: float  # WGS84
    lon: float  # WGS84
    format: Literal["xml", "json", "jsonv2", "geojson", "geocodejson"] = "jsonv2"  # server default: xml
    json_callback: str | None = None  # JSONP wrapper function name
    addressdetails: Flag | None = None  # server default 1
    extratags: Flag | None = None  # server default 0
    namedetails: Flag | None = None  # server default 0
    entrances: Flag | None = None  # server default 0
    accept_language: str | None = Field(default=None, serialization_alias="accept-language")
    # 3 country, 5 state, 8 county, 10 city, 12 town/borough, 13 village/suburb,
    # 14 neighbourhood, 15 any settlement, 16 major streets, 17 major+minor streets, 18 building
    zoom: int | None = Field(default=None, ge=0, le=18)  # server default 18
    layer: list[Layer] | None = None  # sent comma-separated; server default address,poi
    polygon_geojson: Flag | None = None
    polygon_kml: Flag | None = None
    polygon_svg: Flag | None = None
    polygon_text: Flag | None = None
    polygon_threshold: float | None = None  # simplification tolerance in degrees, default 0.0
    email: str | None = None  # contact address for heavy users
    debug: Flag | None = None  # returns HTML debug output, not JSON

    @field_serializer("layer")
    def _comma_join(self, v: list[str] | None) -> str | None:
        return None if v is None else ",".join(v)


# ----------------------------------------- 2. Response ------------------------------------------ #


class ReverseResponse(ApiResponse):
    """200 jsonv2 body of GET /reverse.

    Docs: https://nominatim.org/release-docs/latest/api/Output/#json
    NB: when nothing is found (e.g. offshore) the server returns HTTP 200 with only
    {"error": "Unable to geocode"}; bad params give HTTP 400 {"error": {"code", "message"}}.
    Hence every result field is optional and `error` is modelled here.
    """

    error: str | ReverseErrorDetail | None = None

    place_id: int | None = None  # internal, not stable across servers/reimports
    licence: str | None = None
    osm_type: Literal["node", "way", "relation"] | None = None
    osm_id: int | None = None
    lat: str | None = None  # decimal string, centroid of the matched object
    lon: str | None = None  # decimal string
    category: str | None = None  # OSM tag key, e.g. "highway"
    type: str | None = None  # OSM tag value, e.g. "secondary"
    place_rank: int | None = None  # 0-30 search rank
    importance: float | None = None
    addresstype: str | None = None  # key in `address` that names this object
    name: str | None = None
    display_name: str | None = None
    address: ReverseAddress | None = None  # absent if addressdetails=0
    extratags: dict[str, str] | None = None  # only if extratags=1; may be null
    namedetails: dict[str, str] | None = None  # only if namedetails=1; may be null
    entrances: list[dict[str, Any]] | None = None  # only if entrances=1; null seen live
    boundingbox: list[str] | None = Field(
        default=None, min_length=4, max_length=4
    )  # [min lat, max lat, min lon, max lon]
    geojson: ReverseGeoJson | None = None  # polygon_geojson=1
    geokml: str | None = None  # polygon_kml=1
    svg: str | None = None  # polygon_svg=1
    geotext: str | None = None  # polygon_text=1 (WKT)


# ------------------------------------ 3. Response sub-models ------------------------------------ #


class ReverseAddress(ApiResponse):
    """`address` object of a jsonv2 result.

    Key set is open-ended by design (any OSM place/POI class can appear as a key, e.g. "amenity",
    "historic"), so this is the one place extras are allowed, typed as strings.

    Docs: https://nominatim.org/release-docs/latest/api/Output/#addressdetails
    """

    model_config = ConfigDict(extra="allow")
    __pydantic_extra__: dict[str, str] = Field(init=False)

    # POI / building level
    amenity: str | None = None
    historic: str | None = None
    house_number: str | None = None
    house_name: str | None = None
    road: str | None = None
    # sub-settlement
    neighbourhood: str | None = None
    allotments: str | None = None
    quarter: str | None = None
    city_block: str | None = None
    residential: str | None = None
    farm: str | None = None
    farmyard: str | None = None
    industrial: str | None = None
    commercial: str | None = None
    retail: str | None = None
    hamlet: str | None = None
    croft: str | None = None
    isolated_dwelling: str | None = None
    # settlement
    suburb: str | None = None
    borough: str | None = None
    city_district: str | None = None
    district: str | None = None
    subdivision: str | None = None
    village: str | None = None
    town: str | None = None
    city: str | None = None
    municipality: str | None = None
    # administrative
    county: str | None = None
    state_district: str | None = None
    state: str | None = None
    region: str | None = None
    iso3166_2_lvl4: str | None = Field(default=None, alias="ISO3166-2-lvl4")  # e.g. GB-ENG
    iso3166_2_lvl6: str | None = Field(default=None, alias="ISO3166-2-lvl6")  # e.g. GB-DAL
    iso3166_2_lvl8: str | None = Field(default=None, alias="ISO3166-2-lvl8")  # e.g. GB-WSM (seen live)
    postcode: str | None = None
    country: str | None = None
    country_code: str | None = None  # lowercase ISO 3166-1 alpha-2
    continent: str | None = None


class ReverseGeoJson(ApiResponse):
    """GeoJSON geometry returned when polygon_geojson=1."""

    type: Literal["Point", "LineString", "Polygon", "MultiPoint", "MultiLineString", "MultiPolygon"]
    coordinates: list[Any]  # lon/lat order, nesting depends on `type`


class ReverseErrorDetail(ApiResponse):
    """Structured error (HTTP 4xx), e.g. bad parameter."""

    code: int
    message: str
