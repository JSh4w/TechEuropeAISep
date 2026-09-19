"""Consenting route and local planning authority (LPA) lookup, from planning.data.gov.uk."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import httpx
from pydantic import BaseModel

from bessible.api.planning_data import BASE_URL, EntitySearchRequest, EntitySearchResponse, LocalPlanningAuthority

if TYPE_CHECKING:
    from bessible.models import Position

log = logging.getLogger(__name__)

LPA_DATASET = "local-planning-authority"

ROUTE_ENGLAND = "Local planning authority consent (Town and Country Planning Act 1990)"
ROUTE_NOTE = (
    "Standalone battery storage was removed from the Nationally Significant Infrastructure regime "
    "in England in 2020, so any size is consented by the local planning authority and no "
    "Development Consent Order threshold applies."
)


class LpaLookup(BaseModel):
    """The LPA whose boundary contains a position."""

    entity: int
    reference: str  # ONS LPA code, e.g. E60000002
    name: str

    @property
    def source_url(self) -> str:
        """Entity page on planning.data.gov.uk, the evidence for the lookup."""
        return f"{BASE_URL}/entity/{self.entity}"


class RouteStatement(BaseModel):
    """Consenting route for a site, independent of battery size."""

    route: str
    note: str
    lpa: LpaLookup | None = None


async def lookup_lpa(pos: Position, client: httpx.AsyncClient | None = None) -> LpaLookup | None:
    """Return the LPA containing `pos`, or None if not found or the platform is unreachable."""
    req = EntitySearchRequest(
        latitude=pos.lat,
        longitude=pos.lon,
        dataset=[LPA_DATASET],
        exclude_field=["geometry"],
        limit=1,
    )
    try:
        async with client or httpx.AsyncClient(timeout=20) as http:
            resp = await http.get(EntitySearchRequest.URL, params=req.params())
            resp.raise_for_status()
            parsed = EntitySearchResponse.model_validate(resp.json())
    except (httpx.HTTPError, ValueError):
        log.warning("LPA lookup failed for %s", pos, exc_info=True)
        return None

    for ent in parsed.entities:
        if isinstance(ent, LocalPlanningAuthority) and ent.entity is not None and ent.reference and ent.name:
            return LpaLookup(entity=ent.entity, reference=ent.reference, name=ent.name)
    return None


def consenting_route(lpa: LpaLookup | None) -> RouteStatement:
    """State the consenting route. The route does not depend on capacity."""
    if lpa is None:
        note = (
            f"{ROUTE_NOTE} The local planning authority could not be found: the platform covers "
            "England only, and the lookup may also have failed."
        )
        return RouteStatement(route=ROUTE_ENGLAND, note=note)
    return RouteStatement(route=ROUTE_ENGLAND, note=ROUTE_NOTE, lpa=lpa)
