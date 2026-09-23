"""Google Routes API — Compute Routes (road route between two points). Needs an API key.

Docs: https://developers.google.com/maps/documentation/routes/compute_route_directions
Billing: only Essentials features are modelled here (no traffic, waypoints, tolls), so a call bills as
"Compute Routes Essentials". The field mask limits the response to the two fields below.
"""

from __future__ import annotations

from typing import ClassVar, Literal

from pydantic import Field

from .base import ApiRequest, ApiResponse

URL = "https://routes.googleapis.com/directions/v2:computeRoutes"
FIELD_MASK = "routes.distanceMeters,routes.polyline.encodedPolyline"


# ------------------------------------------ 1. Request ------------------------------------------ #


class LatLng(ApiRequest):
    """WGS84 point."""

    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class Location(ApiRequest):
    """A location given as a point."""

    lat_lng: LatLng = Field(alias="latLng")


class Waypoint(ApiRequest):
    """Origin or destination."""

    location: Location


class RouteModifiers(ApiRequest):
    """Road types to avoid (Essentials)."""

    avoid_highways: bool | None = Field(default=None, alias="avoidHighways")


class ComputeRoutesRequest(ApiRequest):
    """POST body. Send with headers `X-Goog-Api-Key` and `X-Goog-FieldMask: FIELD_MASK`."""

    URL: ClassVar[str] = URL
    METHOD: ClassVar[str] = "POST"

    origin: Waypoint
    destination: Waypoint
    travel_mode: Literal["DRIVE", "WALK", "BICYCLE"] = Field(default="DRIVE", alias="travelMode")
    # DRIVE only: the API rejects a routing preference or road modifiers for WALK / BICYCLE
    routing_preference: Literal["TRAFFIC_UNAWARE"] | None = Field(default=None, alias="routingPreference")
    route_modifiers: RouteModifiers | None = Field(default=None, alias="routeModifiers")

    @classmethod
    def between(
        cls,
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float,
        *,
        travel_mode: Literal["DRIVE", "WALK", "BICYCLE"] = "DRIVE",
    ) -> ComputeRoutesRequest:
        """Route from (lat1, lon1) to (lat2, lon2); a DRIVE route ignores traffic and avoids motorways."""

        def point(lat: float, lon: float) -> Waypoint:
            return Waypoint(location=Location(lat_lng=LatLng(latitude=lat, longitude=lon)))

        drive = travel_mode == "DRIVE"
        return cls(
            origin=point(lat1, lon1),
            destination=point(lat2, lon2),
            travel_mode=travel_mode,
            routing_preference="TRAFFIC_UNAWARE" if drive else None,
            route_modifiers=RouteModifiers(avoid_highways=True) if drive else None,
        )


# ------------------------------------------ 2. Response ----------------------------------------- #


class Polyline(ApiResponse):
    """Route geometry."""

    encoded_polyline: str = Field(alias="encodedPolyline")


class Route(ApiResponse):
    """One route, limited to the fields in FIELD_MASK."""

    distance_meters: int | None = Field(default=None, alias="distanceMeters")  # absent when 0
    polyline: Polyline | None = None


class ComputeRoutesResponse(ApiResponse):
    """Routes found, best first."""

    routes: list[Route] = Field(default_factory=list)  # `{}` when no route exists


# ------------------------------------------ 3. Helpers ------------------------------------------ #


CONTINUATION_BIT = 0x20


def decode_polyline(encoded: str) -> list[tuple[float, float]]:
    """(lat, lon) points of a Google encoded polyline (precision 5).

    https://developers.google.com/maps/documentation/utilities/polylinealgorithm
    """
    points: list[tuple[float, float]] = []
    index = lat = lon = 0
    while index < len(encoded):
        deltas = []
        for _ in range(2):
            shift = result = 0
            while True:
                byte = ord(encoded[index]) - 63
                index += 1
                result |= (byte & 0x1F) << shift
                shift += 5
                if byte < CONTINUATION_BIT:
                    break
            deltas.append(~(result >> 1) if result & 1 else result >> 1)
        lat += deltas[0]
        lon += deltas[1]
        points.append((lat / 1e5, lon / 1e5))
    return points
