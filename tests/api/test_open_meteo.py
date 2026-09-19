from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from bessible.api.open_meteo import ElevationError, ElevationRequest, ElevationResponse

FIX = Path(__file__).parent / "fixtures"


def load(name):
    return json.loads((FIX / name).read_text())


def test_single():
    assert ElevationResponse.model_validate(load("open_meteo_single.json")).elevation == [49.0]


def test_multi():
    assert ElevationResponse.model_validate(load("open_meteo_multi.json")).elevation == [49.0, 61.0, 22.0]


def test_error():
    e = ElevationError.model_validate(load("open_meteo_error.json"))
    assert e.error is True
    assert "same number" in e.reason


def test_params():
    r = ElevationRequest(latitude=[54.5295, 51.233], longitude=[-1.4992, -0.33])
    assert r.params() == {"latitude": "54.5295,51.233", "longitude": "-1.4992,-0.33"}
    assert ElevationRequest(latitude=[1.0], longitude=[2.0], apikey="k").params() == {
        "latitude": "1.0",
        "longitude": "2.0",
        "apikey": "k",
    }


def test_length_mismatch():
    with pytest.raises(ValidationError):
        ElevationRequest(latitude=[1.0, 2.0], longitude=[1.0])
