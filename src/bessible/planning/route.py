"""Consenting route and local planning authority (LPA) lookup, from planning.data.gov.uk."""

from __future__ import annotations

import logging
from http import HTTPStatus
from typing import TYPE_CHECKING

import httpx
from pydantic import BaseModel

from bessible.api.planning_data import BASE_URL, EntitySearchRequest, EntitySearchResponse, LocalPlanningAuthority
from bessible.api.postcodes_io import ReverseGeocodeRequest, ReverseGeocodeResponse

if TYPE_CHECKING:
    from bessible.models import Position

log = logging.getLogger(__name__)

LPA_DATASET = "local-planning-authority"

ROUTE_ENGLAND = "Local planning authority consent (Town and Country Planning Act 1990)"
ROUTE_OUTSIDE_ENGLAND = "England consenting route does not apply"
ROUTE_NOTE = (
    "Standalone battery storage was removed from the Nationally Significant Infrastructure regime "
    "in England in 2020, so any size is consented by the local planning authority and no "
    "Development Consent Order threshold applies."
)


class LpaLookup(BaseModel):
    """The LPA whose boundary contains a position."""

    entity: int | None = None
    reference: str  # ONS LPA code, e.g. E60000002
    name: str
    country: str = "England"

    @property
    def source_url(self) -> str:
        """Entity page on planning.data.gov.uk or postcodes.io, the evidence for the lookup."""
        if self.entity is not None:
            return f"{BASE_URL}/entity/{self.entity}"
        return "https://api.postcodes.io"


class RouteStatement(BaseModel):
    """Consenting route for a site, independent of battery size."""

    route: str
    note: str
    lpa: LpaLookup | None = None
    country: str = "England"


async def _fetch_planning_lpa(pos: Position, client: httpx.AsyncClient | None = None) -> LpaLookup | None:
    req = EntitySearchRequest(
        latitude=pos.lat,
        longitude=pos.lon,
        dataset=[LPA_DATASET],
        exclude_field=["geometry"],
        limit=1,
    )
    if client is None:
        async with httpx.AsyncClient(timeout=20) as http:
            resp = await http.get(EntitySearchRequest.URL, params=req.params())
    else:
        resp = await client.get(EntitySearchRequest.URL, params=req.params())

    if resp.status_code != HTTPStatus.OK:
        return None

    parsed = EntitySearchResponse.model_validate(resp.json())
    for ent in parsed.entities:
        if isinstance(ent, LocalPlanningAuthority) and ent.entity is not None and ent.reference and ent.name:
            return LpaLookup(entity=ent.entity, reference=ent.reference, name=ent.name, country="England")
    return None


async def _fetch_postcode_fallback(pos: Position, client: httpx.AsyncClient | None = None) -> LpaLookup | None:
    rev_req = ReverseGeocodeRequest(lat=pos.lat, lon=pos.lon, limit=1)
    if client is None:
        async with httpx.AsyncClient(timeout=10) as http:
            resp = await http.get(rev_req.URL, params=rev_req.params())
    else:
        resp = await client.get(rev_req.URL, params=rev_req.params())

    if resp.status_code != HTTPStatus.OK:
        return None

    rev_resp = ReverseGeocodeResponse.model_validate(resp.json())
    if rev_resp.result:
        item = rev_resp.result[0]
        return LpaLookup(
            entity=None,
            reference=item.codes.admin_district or "",
            name=item.admin_district or "Unknown",
            country=item.country,
        )
    return None


async def lookup_lpa(pos: Position, client: httpx.AsyncClient | None = None) -> LpaLookup | None:
    """Return the LPA containing `pos`, or None if not found or the platform is unreachable."""
    try:
        found = await _fetch_planning_lpa(pos, client)
        if found is not None:
            return found
    except (httpx.HTTPError, ValueError):
        log.warning("planning.data.gov.uk LPA lookup failed for %s", pos, exc_info=True)

    try:
        return await _fetch_postcode_fallback(pos, client)
    except (httpx.HTTPError, ValueError):
        log.warning("postcodes.io reverse geocode failed for %s", pos, exc_info=True)

    return None


def consenting_route(
    lpa: LpaLookup | None,
    country: str = "England",
    mw: float | None = None,  # ruff: ignore[unused-function-argument]
) -> RouteStatement:
    """State the consenting route. The route does not depend on capacity."""
    effective_country = lpa.country if lpa and lpa.country else country
    if effective_country != "England":
        note = (
            f"The site is in {effective_country}. "
            "The England-specific consenting route does not apply "
            "and NSIP regime rules do not apply."
        )
        return RouteStatement(route=ROUTE_OUTSIDE_ENGLAND, note=note, lpa=lpa, country=effective_country)

    if lpa is None:
        note = (
            f"{ROUTE_NOTE} The local planning authority could not be found: the platform covers "
            "England only, and the lookup may also have failed."
        )
        return RouteStatement(route=ROUTE_ENGLAND, note=note, country=effective_country)

    return RouteStatement(route=ROUTE_ENGLAND, note=ROUTE_NOTE, lpa=lpa, country=effective_country)
