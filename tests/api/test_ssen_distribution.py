from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from bessible.api import ssen_distribution as sd

FIX = Path(__file__).parent / "fixtures"
WESTBURY = (51.246403, -2.198739)


def load(name):
    return json.loads((FIX / f"ssen_distribution_{name}_westbury.json").read_text())


def test_headroom():
    result = sd.HeadroomResponse.model_validate(load("headroom")).result
    assert result.total > len(result.records) > 0  # fixture is trimmed to the nearest rows
    km, site = sd.nearest(result.records, *WESTBURY, max_km=10)[0]
    assert (site.substation, site.substation_type, site.licence_area) == (
        "Westbury Primary",
        "Primary",
        "England / SEPD",
    )
    assert km == pytest.approx(2.3, abs=0.1)
    assert site.estimated_generation_headroom_mw == 0  # text "0.00" upstream
    assert site.estimated_demand_headroom_mva == pytest.approx(10.38)
    assert (site.substation_generation_rag_status, site.generation_constraint) == ("Red", "Upstream Thermal Capacity")
    assert sd.clean_site_name(site.upstream_gsp) == "Melksham"


def test_headroom_not_available_is_none():
    rows = sd.HeadroomResponse.model_validate(load("headroom")).result.records
    assert any(r.estimated_generation_headroom_mw is None for r in rows)  # "N/A" upstream


def test_ecr():
    rows = sd.EcrResponse.model_validate(load("ecr")).result.records
    near = sd.nearest(rows, *WESTBURY, max_km=10)
    assert len(near) == len(rows) > 0
    assert all(isinstance(r.lat, float) and r.registered_capacity_1_mw >= 1 for r in rows)  # lat/lon are text upstream
    assert {r.connection_status for r in rows} <= {"CONNECTED", "ACCEPTED TO CONNECT"}
    assert all(r.energy_source_2 != "DATA NOT AVAILABLE" for r in rows)


@pytest.mark.parametrize(
    ("raw", "clean"), [("Melksham GSP", "Melksham"), ("Frome BSP", "Frome"), ("Westbury Primary", "Westbury")]
)
def test_clean_site_name(raw, clean):
    assert sd.clean_site_name(raw) == clean


def test_requests():
    req = sd.headroom_request()
    assert req.URL == "https://data-api.ssen.co.uk/api/3/action/datastore_search"
    assert req.params() == {"resource_id": sd.HEADROOM_RESOURCE_ID, "limit": 32000}
    assert json.loads(sd.ecr_request(storage_only=True).params()["filters"]) == {
        "Energy Source 1": sd.STORAGE_ENERGY_SOURCE
    }
    assert "Mozilla" in sd.HEADERS["User-Agent"]  # Cloudflare 403s default client agents


def test_forbid():
    with pytest.raises(ValidationError):
        sd.HeadroomSite.model_validate({"Substation": "x", "brand_new_field": 1})
