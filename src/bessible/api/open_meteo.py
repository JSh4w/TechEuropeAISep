"""Open-Meteo Elevation API (Copernicus DEM GLO-90, 90 m resolution).

Docs: https://open-meteo.com/en/docs/elevation-api
"""

from __future__ import annotations

from typing import ClassVar, Literal

from pydantic import Field, field_serializer, model_validator

from .base import ApiRequest, ApiResponse

# ------------------------------------------ 1. Request ------------------------------------------ #


class ElevationRequest(ApiRequest):
    """GET https://api.open-meteo.com/v1/elevation — terrain elevation for up to 100 points.

    Docs: https://open-meteo.com/en/docs/elevation-api
    """

    URL: ClassVar[str] = "https://api.open-meteo.com/v1/elevation"
    METHOD: ClassVar[str] = "GET"

    # WGS84 degrees; up to 100 points per call, sent comma-separated. Lengths must match.
    latitude: list[float] = Field(min_length=1, max_length=100)
    longitude: list[float] = Field(min_length=1, max_length=100)
    # Only for commercial use (customer-api.open-meteo.com); not needed on the free host.
    apikey: str | None = None

    @model_validator(mode="after")
    def _same_length(self) -> ElevationRequest:
        if len(self.latitude) != len(self.longitude):
            msg = "latitude and longitude must have the same number of elements"
            raise ValueError(msg)
        return self

    @field_serializer("latitude", "longitude")
    def _comma_join(self, v: list[float]) -> str:
        return ",".join(str(x) for x in v)


# ----------------------------------------- 2. Response ------------------------------------------ #


class ElevationResponse(ApiResponse):
    """200 body of GET /v1/elevation.

    https://open-meteo.com/en/docs/elevation-api
    """

    # Metres above sea level, one per input coordinate, same order.
    elevation: list[float]


class ElevationError(ApiResponse):
    """HTTP 400 error body of GET /v1/elevation.

    https://open-meteo.com/en/docs/elevation-api
    """

    error: Literal[True]
    reason: str
