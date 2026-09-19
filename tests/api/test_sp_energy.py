from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from bessible.api import opendatasoft, sp_energy

FIX = Path(__file__).parent / "fixtures"


def load(name: str):
    return json.loads((FIX / f"sp_energy_{name}.json").read_text())


def test_capacity_heatmap_spd():
    data = load("capacity_heatmap_spd_glasgow")
    r = sp_energy.DATASETS["capacity_heatmap_spd"].parse(data)
    assert r.total_count == 1
    site = r.results[0]
    assert site.name == "Charlotte Street 33kV"
    assert site.effective_name == "Charlotte Street 33kV"
    assert site.type == "Primary"
    assert site.area == "SPD"
    assert site.effective_lat == pytest.approx(55.8540)
    assert site.effective_lon == pytest.approx(-4.2415)
    assert site.demandavailablecapacity == 16.5
    assert site.generationavailablecapacity == "22.5"
    assert site.demandconstraint == "GREEN"
    assert site.generationconstraint == "GREEN"
    assert site.effective_gsp == "Strathaven"
    assert site.effective_voltage_kv == 33.0


def test_capacity_heatmap_spm():
    data = load("capacity_heatmap_spm_chester")
    r = sp_energy.DATASETS["capacity_heatmap_spm"].parse(data)
    assert r.total_count == 1
    site = r.results[0]
    assert site.name == "Chester City 33kV"
    assert site.site_name == "Chester City 33kV"
    assert site.effective_name == "Chester City 33kV"
    assert site.area == "SPM"
    assert site.effective_lat == pytest.approx(53.1905)
    assert site.effective_lon == pytest.approx(-2.8910)
    assert site.demandavailablecapacity == 25.0
    assert site.generationavailablecapacity == "18.0"
    assert site.demandconstraint == "GREEN"
    assert site.generationconstraint == "AMBER"
    assert site.effective_gsp == "Capenhurst"
    assert site.bsp == "Chester BSP"
    assert site.effective_voltage_kv == 33.0


def test_embedded_capacity_register():
    data = load("embedded_capacity_register_glasgow")
    r = sp_energy.DATASETS["embedded_capacity_register"].parse(data)
    assert r.total_count == 1
    rec = r.results[0]
    assert rec.customer_site == "Glasgow Green BESS"
    assert rec.customer_name == "Clyde Energy Storage Ltd"
    assert rec.energy_source_1.startswith("Stored Energy")
    assert rec.energy_conversion_technology_1 == "Storage (Battery)"
    assert rec.connection_status == "Accepted to Connect"
    assert rec.registered_capacity_1_mw == "20.0"
    assert rec.storage_capacity_1_mwh == "40.0"
    assert rec.coordinates is not None
    assert rec.coordinates.lat == pytest.approx(55.852)
    assert rec.coordinates.lon == pytest.approx(-4.242)


def test_lines():
    data = load("lines_spd_glasgow")
    r = sp_energy.DATASETS["lines_spd"].parse(data)
    assert r.total_count == 1
    line = r.results[0]
    assert line.voltage == 33.0
    assert line.status == "In Service"
    assert line.lic_area == "SPD"
    assert line.geo_shape is not None
    assert line.geo_shape.geometry.type == "LineString"


def test_substations():
    data = load("substations_spd_glasgow")
    r = sp_energy.DATASETS["substations_spd"].parse(data)
    assert r.total_count == 1
    sub = r.results[0]
    assert sub.sub_name == "Charlotte Street 33kV"
    assert sub.voltage == 33.0
    assert sub.asset_type == "Substation"
    assert sub.geo_point_2d is not None
    assert sub.geo_point_2d.lat == pytest.approx(55.8540)


def test_transmission_generation():
    data = load("transmission_generation_glasgow")
    r = sp_energy.DATASETS["transmission_generation"].parse(data)
    assert r.total_count == 1
    tg = r.results[0]
    assert tg.projectname == "Strathclyde BESS"
    assert tg.connectionsite == "Strathaven 275kV Substation"
    assert tg.cumulativetotalcapacity_mw == 50.0
    assert tg.planttype == "Energy Storage System"


def test_clean_site_name():
    assert sp_energy.clean_site_name("Strathaven GSP") == "Strathaven"
    assert sp_energy.clean_site_name("Port Dundas BSP") == "Port Dundas"
    assert sp_energy.clean_site_name("Capenhurst 132kV Substation") == "Capenhurst"
    assert sp_energy.clean_site_name("Deeside") == "Deeside"


def test_auth_headers():
    assert sp_energy.auth_headers("test-key") == {"Authorization": "Apikey test-key"}


def test_request_building():
    req = sp_energy.DATASETS["capacity_heatmap_spd"].near(55.854, -4.241, 5000, limit=25)
    assert req.url() == f"{sp_energy.BASE_URL}/catalog/datasets/distribution-capacity-heatmaps-spd/records"
    assert req.params() == {
        "where": "within_distance(coordinates, geom'POINT(-4.241 55.854)', 5000m)",
        "order_by": "distance(coordinates, geom'POINT(-4.241 55.854)')",
        "limit": 25,
    }


def test_error_and_forbid():
    assert opendatasoft.OdsError.model_validate(load("error")).error_code == "ODSQLError"
    with pytest.raises(ValidationError):
        sp_energy.GisPointAsset.model_validate({"sub_name": "x", "unknown_new_field": 123})
