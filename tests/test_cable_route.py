from __future__ import annotations

import json

import httpx
import pytest
from pydantic import SecretStr

from bessible.api.google_routes import FIELD_MASK, decode_polyline
from bessible.cable_route import straight_line, with_cable_route
from bessible.config import settings
from bessible.models import (
    AssessmentRequest,
    CableRoute,
    CapacityOutput,
    ConfirmedSite,
    FinancialInput,
    GridOutput,
    MarketOutput,
    Position,
    TitleOutput,
)
from bessible.stages.capacity import propose
from bessible.stages.financial import financial_model
from bessible.ukpn.snapshot import get_snapshot

SITE = Position(lat=51.2329, lon=-0.3302)
SUBSTATION = Position(lat=51.2375, lon=-0.3265)
# A real Compute Routes response between SITE and SUBSTATION (field mask FIELD_MASK)
ROUTE_JSON = {
    "routes": [
        {
            "distanceMeters": 854,
            "polyline": {
                "encodedPolyline": "gmuwHlm_A^e@{@}Bk@qA{@sAq@{@k@eAuBcH_EbDk@Nk@?[Mi@i@k@u@cBgE{@yAqA`CCPVvC"
            },
        }
    ]
}


def capacity(**update: object) -> CapacityOutput:
    base = CapacityOutput(
        viable=True,
        substation="Dorking Town 11kV",
        firm_mw=8.0,
        ceiling_mw=8.0,
        recommended_mw=8.0,
        distance_km=0.57,
        substation_position=SUBSTATION,
    )
    return base.model_copy(update=update)


def title_json(south: float, west: float, north: float, east: float) -> dict[str, object]:
    """A planning.data title-boundary response holding one rectangular title."""
    ring = [[west, south], [east, south], [east, north], [west, north], [west, south]]
    props = {"entity": 1, "dataset": "title-boundary", "reference": "1", "name": "", "typology": "geography"}
    feature = {"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [ring]}, "properties": props}
    return {"type": "FeatureCollection", "links": {}, "features": [feature]}


NO_TITLE = {"type": "FeatureCollection", "links": {}, "features": []}


def client(
    status: int = 200,
    body: object = ROUTE_JSON,
    title: object = NO_TITLE,
    origin: list[float] | None = None,
) -> httpx.AsyncClient:
    def handle(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":  # planning.data title lookup
            assert request.url.params["dataset"] == "title-boundary"
            return httpx.Response(200, json=title)
        assert request.headers["X-Goog-Api-Key"] == "test-key"
        assert request.headers["X-Goog-FieldMask"] == FIELD_MASK
        sent = json.loads(request.content)
        assert sent["travelMode"] == "WALK"
        assert "routingPreference" not in sent  # the API rejects it for WALK
        assert "routeModifiers" not in sent
        if origin is not None:
            start = sent["origin"]["location"]["latLng"]
            assert [round(start["latitude"], 6), round(start["longitude"], 6)] == origin
        return httpx.Response(status, json=body)

    return httpx.AsyncClient(transport=httpx.MockTransport(handle))


@pytest.fixture
def routes_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "google_routes_api_key", SecretStr("test-key"))


def test_decode_polyline_matches_google_example():
    # https://developers.google.com/maps/documentation/utilities/polylinealgorithm
    assert decode_polyline("_p~iF~ps|U_ulLnnqC_mqNvxq`@") == [(38.5, -120.2), (40.7, -120.95), (43.252, -126.453)]


@pytest.mark.anyio
@pytest.mark.usefixtures("routes_key")
async def test_road_route_joins_site_and_substation():
    out = await with_cable_route(SITE, capacity(), "run-route", client())
    route = out.route
    assert route is not None
    assert route.method == "road"
    assert route.path[0] == SITE
    assert route.path[-1] == SUBSTATION
    assert route.distance_km >= 0.854
    assert route.distance_km >= straight_line(SITE, SUBSTATION).distance_km
    art = out.artifacts[-1]
    assert art.model_used == "google-routes-api"
    assert "along roads and paths" in art.claim


@pytest.mark.anyio
async def test_no_key_falls_back_to_straight_line():
    out = await with_cable_route(SITE, capacity(), "run-route")
    assert out.route == straight_line(SITE, SUBSTATION)
    assert "GOOGLE_ROUTES_API_KEY is not set" in out.artifacts[-1].claim


@pytest.mark.anyio
@pytest.mark.usefixtures("routes_key")
@pytest.mark.parametrize(("status", "body", "reason"), [(403, {}, "returned 403"), (200, {}, "no road route")])
async def test_service_failure_falls_back_to_straight_line(status: int, body: object, reason: str):
    out = await with_cable_route(SITE, capacity(), "run-route", client(status, body))
    assert out.route is not None
    assert out.route.method == "straight_line"
    assert reason in out.artifacts[-1].claim


@pytest.mark.anyio
@pytest.mark.usefixtures("routes_key")
async def test_long_detour_falls_back_to_straight_line():
    # A road route 4x the straight line loops around land a real cable would cross
    detour = {"routes": [{**ROUTE_JSON["routes"][0], "distanceMeters": 4 * 571}]}
    out = await with_cable_route(SITE, capacity(), "run-route", client(body=detour))
    assert out.route == straight_line(SITE, SUBSTATION)
    assert "detour" in out.artifacts[-1].claim


@pytest.mark.anyio
async def test_no_substation_leaves_output_unchanged():
    out = capacity(substation_position=None)
    assert await with_cable_route(SITE, out, "run-route") == out


def test_propose_returns_substation_position():
    out = propose(SITE, get_snapshot(), "run-route", flexible=False)
    assert out.substation is not None
    assert out.substation_position is not None


@pytest.mark.anyio
async def test_financial_model_prices_cable_on_route():
    road = CableRoute(distance_km=3.0, path=[SITE, SUBSTATION], method="road")
    inp = FinancialInput(
        run_id="run-fin-route",
        request=AssessmentRequest(postcode="RH4 1AD"),
        site=ConfirmedSite(
            position=SITE,
            capacity_mw=8.0,
            boundary=TitleOutput(title_number="SY12345", area_m2=5000.0, boundary_geojson={"type": "Polygon"}),
        ),
        capacity=capacity(route=road),
        grid=GridOutput(),
        market=MarketOutput(revenue_gbp_per_mw_year=94000.0),
    )
    cost_art = next(a for a in (await financial_model(inp)).artifacts if "cost" in a.id)
    assert "over 3.00 km, by road" in cost_art.claim


@pytest.mark.anyio
@pytest.mark.usefixtures("routes_key")
async def test_route_leaves_the_title_at_the_edge_nearest_the_substation():
    # The pin is at the south end of a title; the substation is to the north-east, so the cable leaves at that corner
    north_edge = SITE.lat + 0.002
    title = title_json(SITE.lat - 0.001, SITE.lon - 0.001, north_edge, SITE.lon + 0.001)
    exit_ = [round(north_edge, 6), round(SITE.lon + 0.001, 6)]  # the substation is north-east: the NE corner
    # The canned polyline starts at the pin, not the exit, so shorten the road leg to stay under the detour limit
    body = {"routes": [{**ROUTE_JSON["routes"][0], "distanceMeters": 400}]}
    out = await with_cable_route(SITE, capacity(), "run-route", client(body=body, title=title, origin=exit_))
    route = out.route
    assert route is not None
    assert route.method == "road"
    assert route.path[0] == SITE
    assert (round(route.path[1].lat, 6), round(route.path[1].lon, 6)) == tuple(exit_)
    assert route.path[-1] == SUBSTATION
    assert "leaves the title at its edge nearest the substation" in out.artifacts[-1].claim


@pytest.mark.anyio
@pytest.mark.usefixtures("routes_key")
async def test_without_a_title_the_route_starts_at_the_pin():
    pin = [round(SITE.lat, 6), round(SITE.lon, 6)]
    out = await with_cable_route(SITE, capacity(), "run-route", client(origin=pin))
    assert out.route is not None
    assert out.route.path[0] == SITE
    assert "leaves the title" not in out.artifacts[-1].claim
