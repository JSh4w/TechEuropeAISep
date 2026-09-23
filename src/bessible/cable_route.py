"""Cable route from the site to the serving substation: by road (Google Routes API), else a straight line.

Runs after the capacity proposal, which stays pure; this module does the I/O. It never fails a capacity check.
"""

from __future__ import annotations

import logging
from http import HTTPStatus
from typing import TYPE_CHECKING

import httpx
from pydantic import HttpUrl
from shapely.geometry import Point
from shapely.ops import nearest_points

from bessible.api import planning_data
from bessible.api.geo import distance_km
from bessible.api.google_routes import FIELD_MASK, ComputeRoutesRequest, ComputeRoutesResponse, decode_polyline
from bessible.config import settings
from bessible.location import transform
from bessible.location.geometry import Site
from bessible.location.models import Coordinates
from bessible.models import Artifact, CableRoute, Position

if TYPE_CHECKING:
    from shapely.geometry.base import BaseGeometry

    from bessible.models import CapacityOutput

log = logging.getLogger(__name__)

ROUTE_TIMEOUT_S = 5.0
TITLE_TIMEOUT_S = 10.0
ROUTES_DOCS_URL = "https://developers.google.com/maps/documentation/routes/compute_route_directions"


def _km(a: Position, b: Position) -> float:
    return distance_km(a.lat, a.lon, b.lat, b.lon)


def straight_line(site: Position, substation: Position) -> CableRoute:
    """The fallback: a straight line and its great-circle length."""
    return CableRoute(distance_km=round(_km(site, substation), 2), path=[site, substation], method="straight_line")


async def title_at(site: Position, client: httpx.AsyncClient | None = None) -> BaseGeometry | None:
    """The registered title the site sits in (planning.data title boundaries), or None. Never raises."""
    req = planning_data.EntitySearchRequest(
        latitude=site.lat, longitude=site.lon, dataset=["title-boundary"], geometry_relation="intersects"
    )
    try:
        resp = await _get(req.GEOJSON_URL, req.params(), client)
        titles = planning_data.EntityGeoJsonResponse.model_validate(resp.raise_for_status().json())
    except (httpx.HTTPError, ValueError) as exc:
        log.info("no title for the cable route: %s", exc)
        return None
    found = transform.title_boundary(titles, Coordinates(lat=site.lat, lon=site.lon))
    return found[1] if found else None


async def _get(url: str, params: dict[str, object], client: httpx.AsyncClient | None) -> httpx.Response:
    if client is not None:
        return await client.get(url, params=params)  # type: ignore[arg-type]
    async with httpx.AsyncClient(timeout=TITLE_TIMEOUT_S) as http:
        return await http.get(url, params=params)  # type: ignore[arg-type]


def exit_point(site: Position, title: BaseGeometry, substation: Position) -> Position | None:
    """Where the cable leaves the title: its edge point nearest the substation. None if the substation is on it."""
    frame = Site(Coordinates(lat=site.lat, lon=site.lon), title)
    target = frame.to_m(Point(substation.lon, substation.lat))
    if frame.shape_m.covers(target):
        return None
    lon, lat = frame.to_deg(nearest_points(frame.shape_m.boundary, target)[0]).coords[0]
    return Position(lat=lat, lon=lon)


async def road_route(site: Position, substation: Position, client: httpx.AsyncClient | None = None) -> CableRoute:
    """Driving route on local roads (motorways avoided), joined to the site and the substation by short straight legs.

    Raises `LookupError` when there is no key or no route, `httpx.HTTPError` / `ValueError` on a bad response.
    """
    if settings.google_routes_api_key is None:
        msg = "GOOGLE_ROUTES_API_KEY is not set"
        raise LookupError(msg)
    req = ComputeRoutesRequest.between(site.lat, site.lon, substation.lat, substation.lon)
    headers = {"X-Goog-Api-Key": settings.google_routes_api_key.get_secret_value(), "X-Goog-FieldMask": FIELD_MASK}
    if client is None:
        async with httpx.AsyncClient(timeout=ROUTE_TIMEOUT_S) as http:
            resp = await http.post(req.URL, json=req.params(), headers=headers)
    else:
        resp = await client.post(req.URL, json=req.params(), headers=headers)
    if resp.status_code != HTTPStatus.OK:
        msg = f"Routes API returned {resp.status_code}"
        raise LookupError(msg)

    parsed = ComputeRoutesResponse.model_validate(resp.json())
    route = parsed.routes[0] if parsed.routes else None
    if route is None or route.polyline is None:
        msg = "no road route between the site and the substation"
        raise LookupError(msg)

    road = [Position(lat=lat, lon=lon) for lat, lon in decode_polyline(route.polyline.encoded_polyline)]
    road_km = (route.distance_meters or 0) / 1000
    if road:
        # Google snaps both ends to the nearest road; add the off-road legs so the cable reaches both ends
        road_km += _km(site, road[0]) + _km(road[-1], substation)
    return CableRoute(distance_km=round(road_km, 2), path=[site, *road, substation], method="road")


async def with_cable_route(
    site: Position, out: CapacityOutput, run_id: str, client: httpx.AsyncClient | None = None
) -> CapacityOutput:
    """`out` with its cable route and an artifact saying how it was found. Unchanged when there is no substation."""
    if out.substation_position is None:
        return out
    substation = out.substation_position
    name = out.substation or "the serving substation"
    line = straight_line(site, substation)
    # Leave the plot at its edge nearest the substation, so the road route starts on the right side of it
    title = await title_at(site, client) if settings.google_routes_api_key is not None else None
    start = exit_point(site, title, substation) if title is not None else None
    try:
        route = await road_route(start or site, substation, client)
        if start is not None:
            on_site = _km(site, start)
            route = CableRoute(
                distance_km=round(route.distance_km + on_site, 2), path=[site, *route.path], method="road"
            )
    except (LookupError, httpx.HTTPError, ValueError) as exc:  # ValueError covers bad JSON and ValidationError
        log.info("cable route falls back to a straight line: %s", exc)
        reason = str(exc) if isinstance(exc, LookupError) else type(exc).__name__
        route = line
        claim = f"Cable run to {name}: {line.distance_km:g} km straight line (no road route: {reason})"
        confidence, model_used = 0.5, "straight-line"
    else:
        leaves = (
            f"leaves the title at its edge nearest the substation ({_km(site, start):.2f} km on site), then "
            if start is not None
            else ""
        )
        claim = (
            f"Cable route to {name}: {route.distance_km:g} km; {leaves}by road (local roads, motorways avoided); "
            f"straight line {line.distance_km:g} km. The DNO designs the actual route"
        )
        confidence, model_used = 0.7, "google-routes-api"
    art = Artifact(
        id=f"capacity-cable-route-{run_id[:8]}",
        stage="capacity",
        claim=claim,
        source_url=HttpUrl(ROUTES_DOCS_URL),
        confidence=confidence,
        model_used=model_used,
    )
    return out.model_copy(update={"route": route, "artifacts": [*out.artifacts, art]})
