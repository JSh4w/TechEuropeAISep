from __future__ import annotations

import json
from pathlib import Path

from bessible.api.ea_flood import FloodZoneResponse, flood_zone_at_point

FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


def test_flood_zone():
    hit = FloodZoneResponse.model_validate(load("ea_flood_flood_zone_york_hit.json"))
    assert hit.number_matched == 1
    assert hit.features[0].properties.flood_zone == "FZ3"
    assert hit.features[0].geometry is None

    near = FloodZoneResponse.model_validate(load("ea_flood_flood_zone_york_dwithin.json"))
    assert near.number_matched == 70
    assert {f.properties.flood_zone for f in near.features} == {"FZ2", "FZ3"}

    miss = FloodZoneResponse.model_validate(load("ea_flood_flood_zone_darlington_miss.json"))
    assert miss.features == []
    assert miss.number_returned == 0


def test_request_params():
    assert flood_zone_at_point(53.957, -1.083).params() == {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typeNames": "dataset-04532375-a198-476e-985e-0579a0a11b47:Flood_Zones_2_3_Rivers_and_Sea",
        "outputFormat": "application/json",
        "count": 20,
        "propertyName": "origin,flood_zone,flood_source",
        "cql_filter": "INTERSECTS(shape,SRID=4326;POINT(-1.083 53.957))",
    }
    assert (
        flood_zone_at_point(53.957, -1.083, buffer_m=500).cql_filter
        == "DWITHIN(shape,SRID=4326;POINT(-1.083 53.957),500,meters)"
    )
