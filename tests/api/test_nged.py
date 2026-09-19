from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from bessible.api import ckan, nged

FIX = Path(__file__).parent / "fixtures"
BRIDGWATER = (51.128, -3.004)


def load(name):
    return json.loads((FIX / f"nged_{name}.json").read_text())


def test_capacity_map():
    result = nged.CapacityMapResponse.model_validate(load("capacity_map_bridgwater")).result
    assert result.total > len(result.records) > 0  # fixture is trimmed to the nearest rows
    km, site = nged.nearest(result.records, *BRIDGWATER, max_km=10)[0]
    assert (site.name, site.type, site.area) == ("Bridgwater Local", "Primary", "South West")
    assert km < 1
    assert site.generation_contracted_rag in {"red", "amber", "green"}
    assert site.generation_contracted_headroom_mw >= 0
    assert site.demand_total_capacity is None  # "" upstream
    assert nged.clean_site_name(site.gsp) == "Bridgwater"


def test_ecr_projected():
    rows = nged.EcrResponse.model_validate(load("ecr_bridgwater")).result.records
    near = nged.nearest(rows, *BRIDGWATER, max_km=10)
    assert [km for km, _ in near] == sorted(km for km, _ in near)
    assert all(r.registered_capacity_1_mw >= 1 for r in rows)
    assert rows[0].address_line_1 is None  # not in ECR_FIELDS


def test_ecr_full_storage():
    result = nged.EcrResponse.model_validate(load("ecr_storage_full")).result
    assert result.total > 100
    assert all(r.energy_source_1 == nged.STORAGE_ENERGY_SOURCE for r in result.records)
    assert result.records[0].postcode


def test_nearest_skips_rows_without_coordinates():
    rows = [nged.EcrRecord(lat=None, lon=None), nged.EcrRecord(lat=51.13, lon=-3.0), nged.EcrRecord(lat=53, lon=-1)]
    assert [r.lat for _, r in nged.nearest(rows, *BRIDGWATER, max_km=10)] == [51.13]


@pytest.mark.parametrize(
    ("raw", "clean"),
    [
        ("Indian Queens  S.G.P.", "Indian Queens"),
        ("Seabank Sgp", "Seabank"),
        ("Walpole 132Kv S Stn", "Walpole"),
        ("Bridgwater Grid Bsp", "Bridgwater Grid"),
    ],
)
def test_clean_site_name(raw, clean):
    assert nged.clean_site_name(raw) == clean


def test_requests():
    assert nged.auth_headers("tok") == {"Authorization": "tok"}
    cap = nged.capacity_map_request()
    assert cap.URL == "https://connecteddata.nationalgrid.co.uk/api/3/action/datastore_search"
    assert json.loads(cap.params()["filters"]) == {"type": ["Primary", "BSP"]}
    ecr = nged.ecr_request(storage_only=True).params()
    assert ecr["fields"].startswith("_id,customer_site,")
    assert json.loads(ecr["filters"]) == {"energy_source_1": nged.STORAGE_ENERGY_SOURCE}
    assert "fields" not in nged.ecr_request(fields=None).params()


def test_error_and_forbid():
    e = ckan.DatastoreSearchResponse[nged.EcrRecord].model_validate(load("error_not_found"))
    assert e.success is False
    assert e.error.type == "Not Found Error"
    with pytest.raises(ValidationError):
        nged.CapacityMapSite.model_validate({"name": "x", "brand_new_field": 1})
