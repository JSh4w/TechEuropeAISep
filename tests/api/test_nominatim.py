from __future__ import annotations

import json
from pathlib import Path

from bessible.api.nominatim import ReverseErrorDetail, ReverseRequest, ReverseResponse

FIX = Path(__file__).parent / "fixtures"


def load(name):
    return ReverseResponse.model_validate(json.loads((FIX / name).read_text()))


def test_rural():
    r = load("nominatim_rural.json")
    assert r.osm_type == "way"
    assert r.lat == "54.5314045"
    assert r.place_rank == 26
    assert r.address.town == "Darlington"
    assert r.address.iso3166_2_lvl6 == "GB-DAL"
    assert r.extratags["maxspeed"] == "40 mph"
    assert r.namedetails["ref"] == "B6279"
    assert len(r.boundingbox) == 4


def test_urban():
    r = load("nominatim_urban.json")
    assert r.address.city == "City of Westminster"
    assert r.address.iso3166_2_lvl8 == "GB-WSM"
    assert r.address.historic.startswith("Mileage")
    assert r.geojson.type == "Point"


def test_york_entrances_null():
    r = load("nominatim_york.json")
    assert r.address.house_number == "13"
    assert r.entrances is None
    assert "entrances" in r.model_fields_set


def test_minimal_no_address():
    r = load("nominatim_minimal.json")
    assert r.address is None
    assert r.name == "Mole Valley"
    assert r.osm_type == "relation"


def test_offshore_error():
    r = load("nominatim_error.json")
    assert r.error == "Unable to geocode"
    assert r.place_id is None


def test_error_400():
    r = load("nominatim_error_400.json")
    assert isinstance(r.error, ReverseErrorDetail)
    assert r.error.code == 400


def test_params():
    assert ReverseRequest(lat=54.5295, lon=-1.4992).params() == {"lat": 54.5295, "lon": -1.4992, "format": "jsonv2"}
    r = ReverseRequest(
        lat=1,
        lon=2,
        zoom=10,
        addressdetails=1,
        extratags=0,
        accept_language="en",
        layer=["address", "poi"],
        polygon_geojson=1,
    )
    assert r.params() == {
        "lat": 1.0,
        "lon": 2.0,
        "format": "jsonv2",
        "addressdetails": 1,
        "extratags": 0,
        "accept-language": "en",
        "zoom": 10,
        "layer": "address,poi",
        "polygon_geojson": 1,
    }
