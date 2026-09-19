"""postcodes.io — open UK postcode / reverse-geocoding API (no key).

Docs: https://postcodes.io/docs  ·  OpenAPI: https://api.postcodes.io/openapi.json
"""

from __future__ import annotations

from typing import Any, ClassVar
from urllib.parse import quote

from pydantic import Field

from .base import ApiRequest, ApiResponse

BASE_URL = "https://api.postcodes.io"


# ------------------------------------------ 1. Request ------------------------------------------ #


class ReverseGeocodeRequest(ApiRequest):
    """GET /postcodes?lon=&lat= — nearest postcodes to a WGS84 point.

    https://postcodes.io/docs/postcode/reverse-geocode
    """

    URL: ClassVar[str] = f"{BASE_URL}/postcodes"
    METHOD: ClassVar[str] = "GET"

    lon: float = Field(ge=-180, le=180)
    lat: float = Field(ge=-90, le=90)
    radius: int | None = Field(default=None, ge=1, le=2000)  # metres; server default 100
    limit: int | None = Field(default=None, ge=1, le=100)  # server default 10
    # Search up to 20 km, max 10 results; radius and limit>10 are then ignored.
    widesearch: bool | None = None


class PostcodeLookupRequest(ApiRequest):
    """GET /postcodes/{postcode} — look up a single postcode.

    https://postcodes.io/docs/postcode/lookup
    """

    URL: ClassVar[str] = f"{BASE_URL}/postcodes/{{postcode}}"
    METHOD: ClassVar[str] = "GET"

    postcode: str  # path param; spacing/case insensitive

    def url(self) -> str:
        """The lookup URL with the postcode percent-encoded into the path."""
        return self.URL.format(postcode=quote(self.postcode, safe=""))

    def params(self) -> dict[str, Any]:
        """No query parameters; the postcode travels in the path."""
        return {}


class NearestOutcodesRequest(ApiRequest):
    """GET /outcodes?lon=&lat= — nearest outcode centroids.

    https://postcodes.io/docs/outcode/reverse-geocode
    """

    URL: ClassVar[str] = f"{BASE_URL}/outcodes"
    METHOD: ClassVar[str] = "GET"

    lon: float = Field(ge=-180, le=180)
    lat: float = Field(ge=-90, le=90)
    radius: int | None = Field(default=None, ge=1, le=25000)  # metres; server default 5000
    limit: int | None = Field(default=None, ge=1, le=100)  # server default 10


# ----------------------------------------- 2. Response ------------------------------------------ #


class ReverseGeocodeResponse(ApiResponse):
    """Response of GET /postcodes?lon=&lat=. Sorted by distance ascending."""

    status: int
    result: list[PostcodeResult] | None = None  # null when nothing within radius


class PostcodeLookupResponse(ApiResponse):
    """Response of GET /postcodes/{postcode}."""

    status: int
    result: PostcodeResult


class NearestOutcodesResponse(ApiResponse):
    """Response of GET /outcodes?lon=&lat=."""

    status: int
    result: list[OutcodeResult] | None = None  # null when nothing within radius


class PostcodesIoError(ApiResponse):
    """Error body for any non-2xx, e.g. {"status": 404, "error": "Postcode not found"}."""

    status: int
    error: str
    terminated: TerminatedPostcode | None = None


# ------------------------------------ 3. Response sub-models ------------------------------------ #


class PostcodeCodes(ApiResponse):
    """GSS / ONS codes for the named areas on `PostcodeResult`.

    Pseudo codes such as "E99999999" / "L99999999" mean "not applicable".
    """

    admin_district: str | None = None
    admin_county: str | None = None
    admin_ward: str | None = None
    parish: str | None = None
    parliamentary_constituency: str | None = None
    parliamentary_constituency_2024: str | None = None
    ccg: str | None = None
    ccg_id: str | None = None
    ced: str | None = None
    nuts: str | None = None  # ITL code, e.g. "TLC13"
    lsoa: str | None = None
    msoa: str | None = None
    lau2: str | None = None
    pfa: str | None = None
    nhs_region: str | None = None
    ttwa: str | None = None
    national_park: str | None = None
    bua: str | None = None
    icb: str | None = None
    cancer_alliance: str | None = None
    lsoa11: str | None = None
    msoa11: str | None = None
    lsoa21: str | None = None
    msoa21: str | None = None
    oa21: str | None = None
    ruc11: str | None = None
    ruc21: str | None = None
    lep1: str | None = None
    lep2: str | None = None


class PostcodeResult(ApiResponse):
    """One postcode record (OpenAPI `Postcode` / `NearestPostcode`).

    Shared by reverse geocode and lookup. Crown dependencies (IM/JE/GY) have null
    coordinates and most area fields null; Scotland/Wales have null `region`.
    """

    postcode: str
    outcode: str
    incode: str
    quality: int = Field(ge=1, le=9)  # positional quality: 1 best .. 9 no grid ref
    country: str
    eastings: int | None = None  # OSGB36 / EPSG:27700, metres
    northings: int | None = None  # OSGB36 / EPSG:27700, metres
    longitude: float | None = None  # WGS84
    latitude: float | None = None  # WGS84
    distance: float | None = None  # metres from query point; reverse geocode only

    region: str | None = None  # English region; null outside England
    admin_district: str | None = None
    admin_county: str | None = None  # null in unitary authorities
    admin_ward: str | None = None
    parish: str | None = None
    ced: str | None = None  # county electoral division
    parliamentary_constituency: str | None = None
    parliamentary_constituency_2024: str | None = None
    senedd_constituency: str | None = None  # Wales only
    senedd_constituency_no: int | None = None  # Wales only
    european_electoral_region: str | None = None
    nhs_ha: str | None = None
    primary_care_trust: str | None = None
    ccg: str | None = None
    nhs_region: str | None = None
    icb: str | None = None
    cancer_alliance: str | None = None
    pfa: str | None = None  # police force area
    nuts: str | None = None  # ITL (formerly NUTS) area name
    ttwa: str | None = None  # travel to work area
    national_park: str | None = None
    bua: str | None = None  # built-up area (2022)
    lsoa: str | None = None
    msoa: str | None = None
    lsoa11: str | None = None
    msoa11: str | None = None
    lsoa21: str | None = None
    msoa21: str | None = None
    oa21: str | None = None
    ruc11: str | None = None  # rural-urban classification 2011
    ruc21: str | None = None  # rural-urban classification 2021
    lep1: str | None = None
    lep2: str | None = None
    date_of_introduction: str | None = None  # "YYYYMM"
    date_of_termination: str | None = None  # "YYYYMM"; null for live postcodes
    index_of_multiple_deprivation: int | None = None  # IMD rank of LSOA; 0 if n/a
    codes: PostcodeCodes


class OutcodeResult(ApiResponse):
    """One outcode (OpenAPI `Outcode`); list fields are all areas intersecting it."""

    outcode: str
    eastings: int | None = None  # centroid, EPSG:27700
    northings: int | None = None
    longitude: float | None = None  # centroid, WGS84
    latitude: float | None = None
    admin_county: list[str] = Field(default_factory=list)
    admin_district: list[str] = Field(default_factory=list)
    admin_ward: list[str] = Field(default_factory=list)
    country: list[str] = Field(default_factory=list)
    parish: list[str] = Field(default_factory=list)
    parliamentary_constituency: list[str] = Field(default_factory=list)


class TerminatedPostcode(ApiResponse):
    """Attached to a 404 when the postcode existed but has been terminated."""

    postcode: str
    year_terminated: int
    month_terminated: int
    longitude: float | None = None
    latitude: float | None = None
