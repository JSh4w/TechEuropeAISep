from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from bessible.api.natural_england import (
    LAYERS,
    SERVICE_ALC_PROVISIONAL,
    AlcProvisionalProps,
    AncientWoodlandProps,
    ArcGisCountResponse,
    ArcGisErrorResponse,
    ArcGisGeoJsonResponse,
    ArcGisQueryRequest,
    LayerMetadataRequest,
    LayerMetadataResponse,
    SssiImpactRiskZoneProps,
    SssiProps,
    esri_date,
    exceeded_transfer_limit,
    feature_count,
    query_at_point,
)

FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str) -> dict:
    return json.loads((FIXTURES / f"natural_england_{name}.json").read_text())


def test_at_point_params_and_url():
    req = query_at_point(SERVICE_ALC_PROVISIONAL, lat=54.5295, lon=-1.4992)
    assert req.params() == {
        "geometry": "-1.4992,54.5295",
        "geometryType": "esriGeometryPoint",
        "inSR": 4326,
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": "*",
        "returnGeometry": True,
        "outSR": 4326,
        "f": "geojson",
    }
    assert req.url() == (
        "https://services.arcgis.com/JJzESW51TqeY9uat/ArcGIS/rest/services/"
        "Provisional%20Agricultural%20Land%20Classification%20%28ALC%29%20%28England%29/FeatureServer/0/query"
    )


def test_at_point_with_distance_and_extras():
    req = LAYERS["sssi"].at_point(53.9590, -1.0815, distance_m=3000)
    p = req.params()
    assert p["distance"] == 3000
    assert p["units"] == "esriSRUnit_Meter"
    assert req.url().endswith("/SSSI_England/FeatureServer/0/query")

    req = ArcGisQueryRequest(
        service="SSSI_England",
        where="1=1",
        result_record_count=1,
        result_offset=2,
        return_count_only=True,
        order_by_fields="NAME ASC",
        geometry_precision=5,
        max_allowable_offset=0.001,
    )
    assert req.params() == {
        "where": "1=1",
        "resultRecordCount": 1,
        "resultOffset": 2,
        "returnCountOnly": True,
        "orderByFields": "NAME ASC",
        "geometryPrecision": 5,
        "maxAllowableOffset": 0.001,
        "f": "geojson",
    }


def test_metadata_request():
    req = LayerMetadataRequest(service="National_Parks_England")
    assert req.params() == {"f": "json"}
    assert req.url().endswith("/National_Parks_England/FeatureServer/0")


def test_alc_provisional_darlington():
    r = ArcGisGeoJsonResponse[AlcProvisionalProps].model_validate(load("alc_provisional_darlington"))
    assert r.crs.properties.name == "EPSG:4326"
    assert not exceeded_transfer_limit(r)
    (f,) = r.features
    assert f.geometry.type == "MultiPolygon"
    assert f.properties.alc_grade == "Grade 3"
    assert f.properties.objectid == f.id == 1362


def test_sssi_irz_darlington():
    r = ArcGisGeoJsonResponse[SssiImpactRiskZoneProps].model_validate(load("sssi_irz_darlington"))
    assert r.features[0].geometry.type == "Polygon"
    assert r.features[0].properties.irzurl.startswith("https://irz.geodata.org.uk/")


def test_sssi_york_and_empty():
    r = ArcGisGeoJsonResponse[SssiProps].model_validate(load("sssi_york_3km"))
    assert {f.geometry.type for f in r.features} == {"Polygon", "MultiPolygon"}
    assert "Fulford Ings SSSI" in [f.properties.name for f in r.features]
    empty = ArcGisGeoJsonResponse[SssiProps].model_validate(load("sssi_london_empty"))
    assert empty.features == []


def test_ancient_woodland_dorking():
    r = ArcGisGeoJsonResponse[AncientWoodlandProps].model_validate(load("ancient_woodland_dorking_1km"))
    assert {f.properties.status for f in r.features} <= {"ASNW", "PAWS"}
    assert len(r.features) >= 4


def test_every_layer_sample():
    samples = load("samples")
    assert set(samples) == set(LAYERS)
    for key, spec in LAYERS.items():
        r = spec.parse(samples[key])
        assert exceeded_transfer_limit(r)  # resultRecordCount=1 of many
        (f,) = r.features
        assert f.geometry is None  # returnGeometry=false
        assert isinstance(f.properties, spec.props)
        # every wire property is modelled (nothing fell through to extras)
        assert not f.properties.model_extra, (key, f.properties.model_extra)

    np_ = LAYERS["national_parks"].parse(samples["national_parks"]).features[0].properties
    assert np_.desig_date == 1143849600000
    assert esri_date(np_.desig_date) == datetime(2006, 4, 1, tzinfo=UTC)


def test_count_and_error():
    assert feature_count(ArcGisCountResponse.model_validate(load("count"))) == 4128
    assert feature_count(ArcGisCountResponse.model_validate({"count": 7})) == 7
    err = ArcGisErrorResponse.model_validate(load("error"))
    assert err.error.code == 400
    assert err.error.details == ["'Invalid field: BOGUS' parameter is invalid"]


def test_layer_metadata():
    m = LayerMetadataResponse.model_validate(load("layer_metadata_national_parks"))
    assert m.geometry_type == "esriGeometryPolygon"
    assert m.max_record_count == 1000
    assert m.extent.spatial_reference.wkid == 27700
    by_name = {f.name: f for f in m.fields}
    assert by_name["DESIG_DATE"].type == "esriFieldTypeDate"
    assert by_name["NAME"].length == 200
