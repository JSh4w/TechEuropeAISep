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


def test_grid_substation_model():
    from bessible.ukpn.models import GridSubstation

    raw = {
        "sitefunctionallocation": "SPN-S000000008100",
        "licencearea": "South Eastern Power Networks (SPN)",
        "sitename": "LEATHERHEAD 132/33KV",
        "sitetype": "Grid Substation",
        "sitevoltage": 132,
        "transratingsummer": "90.00, 90.00",
        "maxdemandsummer": 35.0,
        "spatial_coordinates": {"lat": 51.255, "lon": -0.335},
    }
    sub = GridSubstation.model_validate(raw)
    assert sub.id == "SPN-S000000008100"
    assert sub.name == "LEATHERHEAD 132/33KV"
    assert sub.voltage_kv == 132
    assert sub.headroom_import_mw == 55.0
    assert sub.headroom_export_mw == 90.0
    assert sub.position.lat == 51.255
    assert sub.position.lon == -0.335


def test_ingest_and_snapshot_load(tmp_path, monkeypatch):
    from unittest.mock import MagicMock

    from pydantic import SecretStr

    from bessible.config import settings
    from bessible.ukpn import ingest
    from bessible.ukpn.snapshot import load_snapshot

    monkeypatch.setattr(settings, "ukpn_api_key", SecretStr("test-key"))
    monkeypatch.setattr(settings, "data_dir", tmp_path)

    heatmap_fixture = load("capacity_heatmap_dorking")
    substations_fixture = load("substations_dorking")
    table6_fixture = load("table6_dorking")
    table2a_fixture = load("table2a_dorking")
    gsp_fixture = load("gsp_project_status_dorking")

    def mock_get(url, *args, **kwargs):  # ruff: ignore[unused-function-argument]
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        if "ukpn-capacity-heatmap" in url:
            mock_resp.json.return_value = heatmap_fixture
        elif "grid-and-primary-sites" in url:
            mock_resp.json.return_value = substations_fixture
        elif "ltds-table-6" in url:
            mock_resp.json.return_value = table6_fixture
        elif "ltds-table-2a" in url:
            mock_resp.json.return_value = table2a_fixture
        elif "gsp-project-status" in url:
            mock_resp.json.return_value = gsp_fixture
        else:
            mock_resp.json.return_value = substations_fixture
        return mock_resp

    mock_client = MagicMock()
    mock_client.get.side_effect = mock_get
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = None
    monkeypatch.setattr(ingest.httpx, "Client", lambda **_kw: mock_client)

    exit_code = ingest.main()
    assert exit_code == 0

    snapshot = load_snapshot(tmp_path / "ukpn")
    assert len(snapshot.substations) > 0
    assert (tmp_path / "ukpn" / "manifest.json").exists()
    manifest = json.loads((tmp_path / "ukpn" / "manifest.json").read_text())
    assert "ukpn-capacity-heatmap" in manifest["datasets"]
    assert "grid-and-primary-sites" in manifest["datasets"]
    assert "ukpn-ltds-table-6-interest-connections" in manifest["datasets"]


def test_tables_without_location_refuse_radius_queries():
    """LTDS table 2a and GSP project status have no geo field: a radius query would be malformed ODSQL."""
    for name in ("table2a", "gsp_project_status"):
        with pytest.raises(ValueError, match="no location field"):
            ukpn.DATASETS[name].near(51.2, -0.3, 5000)
    assert "within_distance(geo_point_2d" in ukpn.DATASETS["capacity_heatmap"].near(51.2, -0.3, 5000).where
