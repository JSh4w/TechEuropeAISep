from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from bessible.api import opendatasoft, ukpn

FIX = Path(__file__).parent / "fixtures"


def load(name):
    return json.loads((FIX / f"ukpn_{name}.json").read_text())


@pytest.mark.parametrize("name", list(ukpn.DATASETS))
def test_every_dataset_parses(name):
    r = ukpn.DATASETS[name].parse(load(f"{name}_dorking"))
    assert r.total_count >= len(r.results) > 0


def test_substations():
    s = ukpn.DATASETS["substations"].parse(load("substations_dorking")).results[0]
    assert (s.sitename, s.sitevoltage, s.sitetype) == ("DORKING TOWN 33/11KV", 33, "Primary Substation")
    assert s.spatial_coordinates.lat == pytest.approx(51.23, abs=0.05)


def test_capacity_heatmap():
    h = ukpn.DATASETS["capacity_heatmap"].parse(load("capacity_heatmap_dorking")).results[0]
    assert h.name == "Dorking Town 11kV"
    assert h.generationconstraint in {"RED", "AMBER", "GREEN"}
    assert h.generationavailablecapacity > 0


def test_embedded_capacity_register():
    e = ukpn.DATASETS["embedded_capacity_register"].parse(load("embedded_capacity_register_dorking")).results[0]
    assert e.customer_site == "Milton Court Farm"
    assert e.energy_source_1.startswith("Stored Energy")
    assert e.registered_capacity_1_mw == pytest.approx(6.0)


def test_overhead_lines():
    line = ukpn.DATASETS["overhead_lines_132kv"].parse(load("overhead_lines_132kv_dorking")).results[0]
    assert line.voltage == "132kV"
    assert line.geo_shape.geometry.type in {"LineString", "MultiLineString"}


def test_error_and_forbid():
    assert opendatasoft.OdsError.model_validate(load("error")).error_code == "ODSQLError"
    with pytest.raises(ValidationError):
        ukpn.GridPrimarySite.model_validate({"sitename": "x", "brand_new_field": 1})


def test_request():
    req = ukpn.DATASETS["overhead_lines_33kv"].near(51.2327, -0.3306, 5000, limit=20)
    assert req.url() == f"{ukpn.BASE_URL}/catalog/datasets/ukpn-33kv-overhead-lines/records"
    assert req.params() == {
        "where": "within_distance(geo_shape, geom'POINT(-0.3306 51.2327)', 5000m)",
        "order_by": "distance(geo_point_2d, geom'POINT(-0.3306 51.2327)')",  # distance() needs a geo_point
        "limit": 20,
    }
    assert opendatasoft.auth_headers("k") == {"Authorization": "Apikey k"}
    with pytest.raises(ValidationError):
        opendatasoft.RecordsRequest(base_url=ukpn.BASE_URL, dataset="x", limit=101)
