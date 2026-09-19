from __future__ import annotations

import json
from pathlib import Path

import pytest

from bessible.api.postcodes_io import (
    NearestOutcodesRequest,
    NearestOutcodesResponse,
    PostcodeLookupRequest,
    PostcodeLookupResponse,
    PostcodesIoError,
    ReverseGeocodeRequest,
    ReverseGeocodeResponse,
)

FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str) -> dict:
    return json.loads((FIXTURES / f"postcodes_io_{name}.json").read_text())


def test_reverse_darlington():
    r = ReverseGeocodeResponse.model_validate(load("reverse_darlington"))
    assert r.status == 200
    first = r.result[0]
    assert first.postcode == "DL1 4BF"
    assert first.admin_district == "Darlington"
    assert first.admin_county is None
    assert first.codes.admin_district == "E06000005"
    assert first.distance == pytest.approx(292.459, abs=1e-3)
    assert r.result[0].distance <= r.result[1].distance


def test_reverse_dorking_has_county():
    r = ReverseGeocodeResponse.model_validate(load("reverse_dorking"))
    assert r.result[0].outcode == "RH4"
    assert r.result[0].admin_county == "Surrey"


def test_reverse_empty():
    assert ReverseGeocodeResponse.model_validate(load("reverse_empty")).result is None


@pytest.mark.parametrize(
    ("name", "country"),
    [
        ("york", "England"),
        ("scotland", "Scotland"),
        ("wales", "Wales"),
        ("jersey", "Channel Islands"),
        ("isle_of_man", "Isle of Man"),
    ],
)
def test_lookup(name, country):
    r = PostcodeLookupResponse.model_validate(load(f"lookup_{name}"))
    assert r.result.country == country
    assert r.result.distance is None
    if country in ("Channel Islands", "Isle of Man"):
        assert r.result.latitude is None
        assert r.result.eastings is None
    if country != "England":
        assert r.result.region is None


def test_outcodes():
    r = NearestOutcodesResponse.model_validate(load("outcodes_darlington"))
    assert r.result[0].outcode == "DL1"
    assert "Darlington" in r.result[0].admin_district


def test_errors():
    e = PostcodesIoError.model_validate(load("error_404"))
    assert (e.status, e.error, e.terminated) == (404, "Postcode not found", None)
    t = PostcodesIoError.model_validate(load("error_404_terminated"))
    assert t.terminated.year_terminated == 1999
    assert PostcodesIoError.model_validate(load("error_400")).status == 400


def test_request_params():
    req = ReverseGeocodeRequest(lon=-1.4992, lat=54.5295, radius=500, limit=3)
    assert req.params() == {"lon": -1.4992, "lat": 54.5295, "radius": 500, "limit": 3}
    assert ReverseGeocodeRequest(lon=0, lat=51, widesearch=True).params() == {
        "lon": 0.0,
        "lat": 51.0,
        "widesearch": True,
    }
    lookup = PostcodeLookupRequest(postcode="YO1 7HH")
    assert lookup.params() == {}
    assert lookup.url() == "https://api.postcodes.io/postcodes/YO1%207HH"
    assert NearestOutcodesRequest(lon=-1.4992, lat=54.5295, limit=2).params() == {
        "lon": -1.4992,
        "lat": 54.5295,
        "limit": 2,
    }
