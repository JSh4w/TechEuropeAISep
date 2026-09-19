from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import get_args

import pytest

from bessible.api import planning_data as pd

FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str):
    return json.loads((FIXTURES / f"planning_data_{name}.json").read_text())


def test_point_search_darlington():
    r = pd.EntitySearchResponse.model_validate(load("entity_darlington"))
    assert r.count == 14
    assert r.links.next is None  # single page -> empty links object
    by_ds = {e.dataset: e for e in r.entities}
    lpa = by_ds["local-planning-authority"]
    assert isinstance(lpa, pd.LocalPlanningAuthority)
    assert (lpa.entity, lpa.reference, lpa.name) == (626002, "E60000002", "Darlington LPA")
    alc = by_ds["agricultural-land-classification"]
    assert isinstance(alc, pd.AgriculturalLandClassification)
    assert alc.agricultural_land_classification_grade == "Grade 3"
    assert alc.name is None  # "" -> None
    assert isinstance(by_ds["title-boundary"], pd.TitleBoundary)
    # unmodelled dataset with only the common fields falls back to the generic base
    nn = by_ds["nutrient-neutrality-catchment"]
    assert type(nn) is pd.EntityBase
    assert nn.point.startswith("POINT")


@pytest.mark.parametrize("name", ["entity_london", "entity_dorking"])
def test_point_search_other_points(name):
    r = pd.EntitySearchResponse.model_validate(load(name))
    assert r.count == len(r.entities)
    assert any(isinstance(e, pd.ConservationArea) for e in r.entities)
    assert all(e.geometry is None for e in r.entities)  # exclude_field=geometry


def test_york_flood_zone():
    r = pd.EntitySearchResponse.model_validate(load("entity_york_flood"))
    zones = [e for e in r.entities if isinstance(e, pd.FloodRiskZone)]
    assert {z.flood_risk_level for z in zones} == {"2", "3"}
    ca = next(e for e in r.entities if isinstance(e, pd.ConservationArea))
    assert ca.designation_date == date(1975, 1, 1)
    assert ca.end_date is None


def test_geometry_and_pagination_links():
    r = pd.EntitySearchResponse.model_validate(load("entity_darlington_geometry"))
    assert all(e.geometry.startswith(("MULTIPOLYGON", "POLYGON")) for e in r.entities)
    r = pd.EntitySearchResponse.model_validate(load("entity_listed-building"))
    assert r.count > 300_000
    assert "offset=3" in r.links.next
    assert r.entities[0].listed_building_grade == "II"


def test_typed_coercion():
    bf = pd.EntitySearchResponse.model_validate(load("entity_brownfield-land")).entities[0]
    assert isinstance(bf, pd.BrownfieldLand)
    assert bf.hectares == pytest.approx(0.26)
    assert bf.minimum_net_dwellings == 15
    assert bf.planning_permission_date == date(2001, 10, 26)
    assert bf.geometry is None
    lp = pd.EntitySearchResponse.model_validate(load("entity_local-plan")).entities[0]
    assert isinstance(lp, pd.LocalPlan)
    assert lp.required_housing == 20000
    assert lp.period_end_date == date(2031, 1, 1)
    assert lp.point is None


def test_field_stripped_entity_falls_back():
    e = pd.parse_entity({"entity": 30010, "name": "Durham & Darlington"})
    assert type(e) is pd.EntityBase


def test_single_entity():
    e = pd.EntityResponse.model_validate(load("entity_610000")).root
    assert isinstance(e, pd.GreenBelt)
    assert (e.entity, e.dataset, e.name) == (610000, "green-belt", "Halton")
    assert e.geometry.startswith("MULTIPOLYGON")
    assert e.local_authority_district == "E06000006"
    assert e.green_belt_core == "Merseyside and Greater Manchester"


def test_geojson():
    r = pd.EntityGeoJsonResponse.model_validate(load("entity_darlington.geojson"))
    assert len(r.features) == 3
    f = r.features[0]
    assert f.geometry.type == "MultiPolygon"
    assert isinstance(f.properties, pd.Parish)
    assert f.properties.name == "Great Burdon"


def test_dataset_list_and_single():
    r = pd.DatasetListResponse.model_validate(load("dataset_list"))
    assert {d.dataset for d in r.datasets} == {"green-belt", "flood-risk-zone"}
    assert len(r.typologies["geography"].dataset) == 2
    d = pd.DatasetResponse.model_validate(load("dataset_green-belt")).root
    assert d.name == "Green belt"
    assert d.entity_count == 181
    assert d.paint_options.colour == "#85994b"
    assert d.entry_date is None


def test_request_params():
    req = pd.EntitySearchRequest(
        latitude=54.5295,
        longitude=-1.4992,
        dataset=["green-belt", "flood-risk-zone"],
        geometry_relation="intersects",
        exclude_field=["geometry"],
        limit=100,
    )
    assert req.params() == {
        "latitude": 54.5295,
        "longitude": -1.4992,
        "dataset": ["green-belt", "flood-risk-zone"],
        "geometry_relation": "intersects",
        "exclude_field": ["geometry"],
        "limit": 100,
    }
    with pytest.raises(ValueError, match="less than or equal to 500"):
        pd.EntitySearchRequest(limit=501)

    e = pd.EntityRequest(entity=610000)
    assert e.url() == "https://www.planning.data.gov.uk/entity/610000.json"
    assert e.params() == {}

    assert pd.DatasetListRequest(dataset=["parish"], include_typologies=False).params() == {
        "dataset": ["parish"],
        "include_typologies": False,
    }
    d = pd.DatasetRequest(dataset="green-belt")
    assert d.url() == "https://www.planning.data.gov.uk/dataset/green-belt.json"
    assert d.params() == {}


def test_bess_datasets_are_modelled():
    assert set(pd.BESS_POINT_DATASETS) <= set(pd.ENTITY_MODELS)
    assert len(pd.ENTITY_MODELS) == 43


def test_entity_union_tags_match_dataset_literals():
    assert len(pd.ENTITY_MODELS) == 43
    for tag, model in pd.ENTITY_MODELS.items():
        assert get_args(model.model_fields["dataset"].annotation) == (tag,)
