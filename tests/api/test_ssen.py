from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from bessible.api import ssen

FIX = Path(__file__).parent / "fixtures"


def load(name):
    return json.loads((FIX / f"ssen_{name}_blackhillock.json").read_text())


@pytest.mark.parametrize("name", [n for n in ssen.DATASETS if n != "substations_132kv"])  # none within 15 km
def test_geo_datasets_parse(name):
    r = ssen.DATASETS[name].parse(load(name))
    assert r.total_count >= len(r.results) > 0


def test_substations():
    subs = ssen.DATASETS["substations_supergrid"].parse(load("substations_supergrid")).results
    assert "BLACKHILLOCK SUBSTATION" in {s.name for s in subs}
    assert subs[0].voltage == 275000
    assert subs[0].geo_point_2d.lat == pytest.approx(57.52, abs=0.05)


@pytest.mark.parametrize("register", list(ssen.REGISTERS))
def test_registers(register):
    rows = ssen.parse_register(load(register)).results
    assert rows
    assert all("blackhillock" in r.connection_site.lower() for r in rows)
    assert rows[0].cumulative_total_capacity_mw >= rows[-1].cumulative_total_capacity_mw
    assert rows[0].host_to == "SHET"


def test_requests():
    req = ssen.DATASETS["overhead_lines_132kv"].near(57.522, -2.945, 5000, limit=20)
    assert req.url() == f"{ssen.BASE_URL}/catalog/datasets/overhead-line-grid/records"
    assert req.params() == {
        "where": "within_distance(geo_shape, geom'POINT(-2.945 57.522)', 5000m)",
        "order_by": "distance(geo_point_2d, geom'POINT(-2.945 57.522)')",
        "limit": 20,
    }
    reg = ssen.register_request("tec_register", "BLACKHILLOCK SUBSTATION", storage_only=True)
    assert reg.url().startswith(ssen.BASE_URL)
    assert reg.params()["where"] == (
        'search(tec_register_records_connection_site, "BLACKHILLOCK") '
        'and search(tec_register_records_plant_type, "Energy Storage System")'
    )
    assert "where" not in ssen.register_request("embedded_register").params()


def test_forbid():
    with pytest.raises(ValidationError):
        ssen.SubstationSite.model_validate({"name": "x", "brand_new_field": 1})
