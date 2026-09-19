"""Opendatasoft Explore API v2.1: the records request, envelope and geo fields shared by every ODS portal.

Used by ``ukpn`` and ``ssen`` (each passes its own ``base_url``).
API docs: https://help.opendatasoft.com/apis/ods-explore-v2/

Notes (verified live 2026-09):
- Auth: header ``Authorization: Apikey <key>`` (see ``auth_headers``). A bad key is HTTP 401.
- ``limit`` is capped at 100 per call; page with ``offset`` (offset + limit <= 10000).
- Errors are HTTP 400 with ``{"error_code": ..., "message": ...}`` -> ``OdsError``.
- Spatial filter: ``within_distance(<geo field>, geom'POINT(lon lat)', <n>m)``; ``distance()`` for sorting
  only accepts geo_point fields.
"""

from __future__ import annotations

from typing import Any, ClassVar, Literal, NamedTuple

from pydantic import Field

from .base import ApiRequest, ApiResponse

# ------------------------------------------ 1. Request ------------------------------------------ #


class RecordsRequest(ApiRequest):
    """GET /catalog/datasets/{dataset}/records - query one dataset with ODSQL.

    https://help.opendatasoft.com/apis/ods-explore-v2/#tag/Dataset/operation/getRecords
    """

    URL: ClassVar[str] = "{base_url}/catalog/datasets/{dataset}/records"
    METHOD: ClassVar[str] = "GET"

    # path params (excluded from params())
    dataset: str
    base_url: str  # portal root, e.g. ukpn.BASE_URL (excluded from params())

    select: str | None = None  # ODSQL select, e.g. "sitename, sitevoltage"
    where: str | None = None  # ODSQL filter, e.g. "sitevoltage >= 33"
    group_by: str | None = None
    order_by: str | None = None  # e.g. "sitevoltage desc"
    limit: int | None = Field(default=None, ge=-1, le=100)  # server default 10
    offset: int | None = Field(default=None, ge=0)
    refine: list[str] | None = None  # facet filters "field:value", repeatable
    exclude: list[str] | None = None
    lang: str | None = None
    timezone: str | None = None

    def url(self) -> str:
        """Return the dataset's records endpoint URL."""
        return self.URL.format(base_url=self.base_url, dataset=self.dataset)

    def params(self) -> dict[str, Any]:
        """Return the query-string parameters (nulls dropped, path param excluded)."""
        return self.model_dump(by_alias=True, exclude_none=True, mode="json", exclude={"dataset", "base_url"})


# ----------------------------------------- 2. Response ------------------------------------------ #


class RecordsResponse[R](ApiResponse):
    """Envelope of a records query."""

    total_count: int  # matches across all pages
    results: list[R]


class OdsError(ApiResponse):
    """HTTP 4xx body."""

    error_code: str  # e.g. "ODSQLError"
    message: str


# ------------------------------------ 3. Response sub-models ------------------------------------ #


class GeoPoint(ApiResponse):
    """A ``geo_point_2d`` field (WGS84)."""

    lon: float
    lat: float


class GeoShapeGeometry(ApiResponse):
    """GeoJSON geometry inside a ``geo_shape`` field."""

    type: Literal["Point", "MultiPoint", "LineString", "MultiLineString", "Polygon", "MultiPolygon"]
    coordinates: list[Any]  # [lon, lat] nesting per RFC 7946


class GeoShape(ApiResponse):
    """A ``geo_shape`` field: a GeoJSON Feature with empty properties."""

    type: Literal["Feature"]
    geometry: GeoShapeGeometry
    properties: dict[str, Any] = Field(default_factory=dict)


# -------------------- 4. Not from the API (helpers, registries, transforms) --------------------- #


def auth_headers(api_key: str) -> dict[str, str]:
    """Request headers carrying the portal API key."""
    return {"Authorization": f"Apikey {api_key}"}


class DatasetSpec[R: ApiResponse](NamedTuple):
    """Registry entry tying a dataset to its geo field and typed response."""

    base_url: str
    dataset: str
    geo_field: str  # the field to filter on with within_distance()
    response: type[RecordsResponse[R]]
    point_field: str | None = None  # geo_point to sort by distance on, when geo_field is a shape

    def near(self, lat: float, lon: float, distance_m: float, limit: int = 100) -> RecordsRequest:
        """Build a query for this dataset's records within `distance_m` metres of a WGS84 point, nearest first.

        ``distance()`` only accepts geo_point fields, so shape datasets sort on `point_field` instead.
        """
        point = f"geom'POINT({lon} {lat})'"  # WKT is lon-lat order
        return RecordsRequest(
            dataset=self.dataset,
            where=f"within_distance({self.geo_field}, {point}, {distance_m}m)",
            order_by=f"distance({self.point_field or self.geo_field}, {point})",
            limit=limit,
            base_url=self.base_url,
        )

    def parse(self, body: dict[str, Any]) -> RecordsResponse[R]:
        """Validate a records body with rows typed by this dataset's model."""
        return self.response.model_validate(body)
