from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from bessible.models import (
    AssessmentRequest,
    CapacityOutput,
    ConfirmedSite,
    GridOutput,
    PlanningInput,
    Position,
    SiteLandOutput,
    TitleOutput,
)
from bessible.planning.route import ROUTE_ENGLAND, LpaLookup, consenting_route, lookup_lpa
from bessible.stages.planning import regulatory_planning

FIXTURE = Path(__file__).parent / "api" / "fixtures" / "planning_data_entity_darlington.json"
POS = Position(lat=54.52, lon=-1.55)


def client(handler: httpx.MockTransport | None = None) -> httpx.AsyncClient:
    def ok(request: httpx.Request) -> httpx.Response:
        assert request.url.params["dataset"] == "local-planning-authority"
        assert request.url.params["latitude"] == "54.52"
        return httpx.Response(200, json=json.loads(FIXTURE.read_text()))

    return httpx.AsyncClient(transport=handler or httpx.MockTransport(ok))


@pytest.mark.anyio
async def test_lookup_lpa_finds_authority():
    lpa = await lookup_lpa(POS, client())
    assert lpa == LpaLookup(entity=626002, reference="E60000002", name="Darlington LPA")
    assert lpa.source_url == "https://www.planning.data.gov.uk/entity/626002"


@pytest.mark.anyio
async def test_lookup_lpa_none_when_no_match():
    empty = httpx.MockTransport(lambda _r: httpx.Response(200, json={"entities": [], "links": {}, "count": 0}))
    assert await lookup_lpa(POS, client(empty)) is None


@pytest.mark.anyio
@pytest.mark.parametrize("status", [500, 404])
async def test_lookup_lpa_none_on_http_error(status):
    down = httpx.MockTransport(lambda _r: httpx.Response(status, text="nope"))
    assert await lookup_lpa(POS, client(down)) is None


def test_route_does_not_depend_on_capacity():
    lpa = LpaLookup(entity=1, reference="E60000001", name="Test LPA")
    assert consenting_route(lpa).route == ROUTE_ENGLAND
    assert "no Development Consent Order threshold" in consenting_route(lpa).note


def test_route_unknown_lpa_keeps_route():
    s = consenting_route(None)
    assert s.route == ROUTE_ENGLAND
    assert s.lpa is None
    assert "could not be found" in s.note


def planning_input() -> PlanningInput:
    req = AssessmentRequest(postcode="DL1 1AA")
    cap = CapacityOutput.model_construct()
    site = ConfirmedSite.model_construct(
        position=POS, capacity_mw=6.0, boundary=TitleOutput.model_construct(), capacity=None, flexible_connection=False
    )
    return PlanningInput.model_construct(
        run_id="planrun-1234",
        request=req,
        site=site,
        capacity=cap,
        grid=GridOutput(),
        site_land=SiteLandOutput(land_use="x"),
    )


@pytest.mark.anyio
async def test_stage_names_lpa_with_source():
    out = await regulatory_planning(planning_input())
    assert "Darlington LPA" in out.consenting_route
    art = out.artifacts[0]
    assert str(art.source_url) == "https://www.planning.data.gov.uk/entity/626002"
    assert "Darlington LPA" in art.claim


@pytest.mark.anyio
async def test_stage_unknown_lpa(monkeypatch):
    async def none(*_a: object, **_k: object) -> None:  # ruff: ignore[unused-async]
        return None

    monkeypatch.setattr("bessible.stages.planning.lookup_lpa", none)
    out = await regulatory_planning(planning_input())
    assert out.consenting_route == ROUTE_ENGLAND
    assert "Authority unknown" in out.artifacts[0].claim
