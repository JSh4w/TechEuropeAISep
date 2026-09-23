from __future__ import annotations

import json
from pathlib import Path

import pytest
from shapely.geometry import box, mapping

from bessible.api import (
    ckan,
    ea_flood,
    natural_england,
    neso,
    nged,
    npg,
    planning_data,
    postcodes_io,
    sp_energy,
    ssen_distribution,
    ukpn,
)
from bessible.location import Coordinates, LocationData, transform
from bessible.location.geometry import Site, from_geojson, to_geometry
from bessible.location.models import Designation, Deterministic

FIX = Path(__file__).parents[1] / "api" / "fixtures"
HERE = Coordinates(lat=51.0, lon=-1.0)


def load(name):
    return json.loads((FIX / f"{name}.json").read_text())


def square(site, x0, y0, x1, y1):
    """GeoJSON of a box given in metres east / north of the site's centre."""
    k, lat0, lon0 = site._kx, site._lat0, site._lon0  # ruff: ignore[private-member-access]
    return mapping(box(lon0 + x0 / k, lat0 + y0 / 110_540, lon0 + x1 / k, lat0 + y1 / 110_540))


@pytest.fixture
def site():
    """A 100 m x 100 m title centred on HERE."""
    frame = Site(HERE)
    return Site(HERE, from_geojson(square(frame, -50, -50, 50, 50)))


# ------------------------------------------- geometry ------------------------------------------- #


def test_measure_overlap_and_distance(site):
    assert site.shape_m.area == pytest.approx(10_000, rel=1e-6)
    assert site.measure(from_geojson(square(site, 0, -50, 50, 50))) == (True, 50.0, 0.0)
    assert site.measure(from_geojson(square(site, 150, -50, 250, 50))) == (False, 0.0, 100.0)


def test_point_site_has_no_overlap():
    point = Site(HERE)
    assert point.measure(from_geojson(square(point, -10, -10, 10, 10))) == (True, None, 0.0)
    assert point.distance_km(51.0, -1.0) == 0


def test_geometry_round_trip(site):
    geometry = to_geometry(site.boundary)
    assert geometry.type == "Polygon"
    # rounded to 6 decimal places (~0.1 m), so equal to well within 1 % on a 100 m square
    assert from_geojson(geometry).symmetric_difference(site.boundary).area < 0.01 * site.boundary.area


# -------------------------------------------- the site ------------------------------------------ #


def test_title_boundary_picks_the_smallest_title():
    response = planning_data.EntityGeoJsonResponse.model_validate(load("planning_data_entity_darlington.geojson"))
    titles = [f for f in response.features if f.properties.dataset == "title-boundary"]
    point = from_geojson(titles[0].geometry.model_dump()).representative_point()
    title, geom = transform.title_boundary(response, Coordinates(lat=point.y, lon=point.x))
    assert title.inspire_id in {f.properties.reference for f in titles}  # never the parish in the same response
    assert title.area_m2 == pytest.approx(title.area_ha * 10_000, rel=1e-3)
    assert title.bbox == geom.bounds
    assert title.source_url.startswith("https://www.planning.data.gov.uk/entity/")


def test_locality_from_postcode_and_planning_data():
    postcode = postcodes_io.ReverseGeocodeResponse.model_validate(load("postcodes_io_reverse_darlington")).result[0]
    entities = planning_data.EntitySearchResponse.model_validate(load("planning_data_entity_darlington")).entities
    where = transform.locality(postcode, None, entities)
    assert where.country == "England"
    assert where.district == "Darlington"
    assert where.planning_authority_code.startswith("E6")
    assert not where.planning_authority.endswith("LPA")
    assert where.place is None
    assert transform.search_terms(where)[-1] != ""


# ---------------------------------------------- land -------------------------------------------- #


def flood_response(site, *zones):
    return ea_flood.FloodZoneResponse.model_validate({
        "type": "FeatureCollection",
        "numberReturned": len(zones),
        "features": [
            {
                "type": "Feature",
                "id": f"fz.{i}",
                "geometry": square(site, *box_m),
                "properties": {"flood_zone": zone, "flood_source": "river", "origin": "modelled"},
            }
            for i, (zone, box_m) in enumerate(zones)
        ],
    })


def test_flood_risk_measures_the_title_not_the_point(site):
    risk = transform.flood_risk(
        flood_response(site, ("FZ2", (-50, -50, 0, 50)), ("FZ3", (-50, -50, -25, 50)), ("FZ3", (80, 0, 90, 10))),
        site,
        [],
    )
    assert (risk.zone, risk.zone_2_pct, risk.zone_3_pct) == (3, 50.0, 25.0)
    assert [z.distance_m for z in risk.zones] == [0, 0, 30]


def test_flood_zone_1_when_zones_only_nearby(site):
    risk = transform.flood_risk(flood_response(site, ("FZ3", (60, 0, 90, 10))), site, [])
    assert (risk.zone, risk.zone_3_pct, risk.zones[0].distance_m) == (1, 0.0, 10.0)


def alc_response(site, *grades):
    return natural_england.LAYERS["alc_post_1988"].parse({
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "id": i,
                "geometry": square(site, *box_m),
                "properties": {"OBJECTID_1": i, "ALC_GRADE": grade, "Published_": "https://example.org/survey"},
            }
            for i, (grade, box_m) in enumerate(grades)
        ],
    })


def provisional_response(site, grade):
    return natural_england.LAYERS["alc_provisional"].parse({
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "id": 1,
                "geometry": square(site, -500, -500, 500, 500),
                "properties": {"OBJECTID": 1, "ALC_GRADE": grade},
            }
        ],
    })


def test_detailed_survey_supersedes_provisional_grade(site):
    survey = alc_response(site, ("Grade 3b", (-50, -50, 0, 50)))
    result, documents = transform.land(provisional_response(site, "Grade 3"), survey, site, [])
    assert [(g.grade, g.overlap_pct, g.survey) for g in result.alc] == [
        ("Grade 3", 50.0, "provisional"),
        ("Grade 3b", 50.0, "post_1988"),
    ]
    assert result.best_and_most_versatile is None  # half the title is still an unsplit grade 3
    assert [d.kind for d in documents] == ["alc_survey_report"]


def test_best_and_most_versatile(site):
    whole = (-50, -50, 50, 50)
    assert transform.land(None, alc_response(site, ("Grade 3a", whole)), site, [])[0].best_and_most_versatile is True
    assert transform.land(None, alc_response(site, ("Grade 3b", whole)), site, [])[0].best_and_most_versatile is False
    assert transform.land(provisional_response(site, "Grade 2"), None, site, [])[0].best_and_most_versatile is True


def test_green_belt_flag(site):
    belt = planning_data.GreenBelt(entity=1, name="Test Green Belt")
    result, _ = transform.land(None, None, site, [belt])
    assert (result.green_belt, result.green_belt_name) == (True, "Test Green Belt")


# ------------------------------------------ designations ---------------------------------------- #


def test_natural_england_designations_are_measured_and_ranged():
    layers = {"sssi": natural_england.LAYERS["sssi"].parse(load("natural_england_sssi_york_3km"))}
    first = from_geojson(layers["sssi"].features[0].geometry.model_dump()).representative_point()
    on_it = Site(Coordinates(lat=first.y, lon=first.x))
    found, documents = transform.natural_england_designations(layers, on_it)
    hit = next(d for d in found if d.on_site)
    assert (hit.kind, hit.category, hit.distance_m) == ("sssi", "ecology", 0)
    assert hit.source_url.startswith("https://designatedsites.naturalengland.org.uk/")
    assert [d.url for d in documents] == [hit.source_url]
    far_away = Site(Coordinates(lat=first.y + 0.1, lon=first.x))  # ~11 km: beyond every range
    assert transform.natural_england_designations(layers, far_away) == ([], [])


def test_planning_designations_near_and_on_site(site):
    k = site._kx  # ruff: ignore[private-member-access]
    listed = planning_data.ListedBuilding.model_validate({
        "entity": 7,
        "name": "Old Barn",
        "reference": "1234567",
        "listed-building-grade": "II*",
        "point": f"POINT ({-1.0 + 80 / k} 51.0)",
    })
    too_far = listed.model_copy(update={"entity": 8, "point": f"POINT ({-1.0 + 900 / k} 51.0)"})
    belt = planning_data.GreenBelt(entity=9, name="Belt", notes="Reviewed 2024")
    found, documents, notes = transform.planning_designations([belt], [listed, too_far], site)
    assert [(d.kind, d.on_site, d.distance_m, d.detail) for d in found] == [
        ("listed_building", False, 30.0, "Grade II*"),
        ("green_belt", True, 0.0, None),
    ]
    assert found[1].overlap_pct is None  # fetched without geometry: only known to touch the title
    assert documents[0].url == "https://historicengland.org.uk/listing/the-list/list-entry/1234567"
    assert notes == ["green-belt Belt: Reviewed 2024"]


def test_local_plans_filtered_by_authority():
    plans = planning_data.EntitySearchResponse.model_validate(load("planning_data_entity_local-plan")).entities
    code = plans[0].local_planning_authorities.split(";")[0]
    documents = transform.local_plan_documents(plans, code)
    assert documents
    assert {d.kind for d in documents} == {"local_plan"}
    assert transform.local_plan_documents(plans, "E60000000") == []
    assert transform.local_plan_documents(plans, None) == []


# ---------------------------------------------- grid -------------------------------------------- #

DORKING = Site(Coordinates(lat=51.23, lon=-0.33))


def ukpn_rows(name):
    return ukpn.DATASETS[name].parse(load(f"ukpn_{name}_dorking")).results


def test_ukpn_substations_merge_heatmap_and_site_list():
    subs = transform.ukpn_substations(ukpn_rows("substations"), ukpn_rows("capacity_heatmap"), DORKING)
    town = next(s for s in subs if s.name.startswith("Dorking Town"))
    assert (town.operator, town.kind, town.gsp, town.tia_threshold_mw) == ("UKPN", "primary", "West Weybridge", 1.0)
    assert town.transformer_ratings_summer_mva == [27.6, 27.6]
    assert town.earthing == "COLD"
    # The site list gives the highest voltage on site (33 kV); a new connection joins the heatmap's 11 kV busbar.
    assert (town.voltage_kv, town.connection_voltage_kv) == (33.0, 11.0)
    assert town.headroom.generation_rag in {"red", "amber", "green"}
    assert town.headroom.demand_unit == "MW"
    assert sum(s.name.upper().startswith("DORKING TOWN") for s in subs) == 1  # merged, not listed twice
    assert any(s.headroom is None for s in subs)  # a site with no heatmap row is still listed


def test_nged_substations():
    records = nged.CapacityMapResponse.model_validate(load("nged_capacity_map_bridgwater")).result.records
    subs = transform.nged_substations(records, Site(Coordinates(lat=51.11, lon=-2.99)))
    assert len(subs) == len(records)
    assert {s.gsp for s in subs} == {"Bridgwater"}  # "Bridgwater  S.G.P." cleaned to match NESO
    assert all("contracted" in s.headroom.basis for s in subs)
    assert all(s.connection_voltage_kv is None for s in subs)  # NGED publishes no voltage here


def test_ssen_distribution_substations():
    records = ssen_distribution.HeadroomResponse.model_validate(
        load("ssen_distribution_headroom_westbury")
    ).result.records
    subs, _ = transform.ssen_distribution_substations(records, Site(Coordinates(lat=51.25, lon=-2.2)))
    assert subs[0].tia_threshold_mw == pytest.approx(5)
    assert subs[0].headroom.demand_unit == "MVA"
    # "33 / 11" -> 11: the lower side is the busbar a new connection joins.
    assert {s.voltages: s.connection_voltage_kv for s in subs}["33 / 11"] == 11.0
    assert all(s.gsp is None or not s.gsp.endswith("GSP") for s in subs)


def test_sp_energy_substations():
    spd_records = sp_energy.DATASETS["capacity_heatmap_spd"].parse(
        load("sp_energy_capacity_heatmap_spd_glasgow")
    ).results
    spm_records = sp_energy.DATASETS["capacity_heatmap_spm"].parse(
        load("sp_energy_capacity_heatmap_spm_chester")
    ).results
    subs = transform.sp_energy_substations(spd_records + spm_records, Site(Coordinates(lat=55.85, lon=-4.25)))
    assert len(subs) == 2
    assert subs[0].operator == "SP Energy Networks"
    assert subs[0].name == "Charlotte Street 33kV"
    assert subs[0].headroom.generation_mw == pytest.approx(22.5)
    assert subs[0].headroom.demand == pytest.approx(16.5)
    assert subs[0].gsp == "Strathaven"
    assert subs[0].connection_voltage_kv == 33.0
    assert subs[1].name == "Chester City 33kV"
    assert subs[1].gsp == "Capenhurst"


@pytest.mark.parametrize(
    ("operator", "records"),
    [
        ("UKPN", lambda: ukpn_rows("embedded_capacity_register")),
        ("NGED", lambda: nged.EcrResponse.model_validate(load("nged_ecr_bridgwater")).result.records),
        (
            "SSEN Distribution",
            lambda: ssen_distribution.EcrResponse.model_validate(load("ssen_distribution_ecr_westbury")).result.records,
        ),
        (
            "SP Energy Networks",
            lambda: sp_energy.DATASETS["embedded_capacity_register"]
            .parse(load("sp_energy_embedded_capacity_register_glasgow"))
            .results,
        ),
    ],
)
def test_grid_projects_share_one_shape(operator, records):
    projects = transform.grid_projects(records(), operator, DORKING)
    assert projects
    assert all(p.capacity_mw is None or p.capacity_mw >= 1 for p in projects)
    assert {p.status for p in projects} <= {"connected", "accepted", None}
    assert {p.status for p in projects} != {None}


def test_storage_projects_are_flagged():
    records = nged.EcrResponse.model_validate(load("nged_ecr_storage_full")).result.records
    projects = transform.grid_projects(records, "NGED", DORKING)
    assert projects
    assert all(p.is_storage and not p.is_solar for p in projects)


def test_overhead_lines_distance_and_crossing(site):
    k = site._kx  # ruff: ignore[private-member-access]
    crossing = {"type": "LineString", "coordinates": [[-1.0 - 200 / k, 51.0], [-1.0 + 200 / k, 51.0]]}
    north = {
        "type": "LineString",
        "coordinates": [[-1.0 - 200 / k, 51.0 + 150 / 110_540], [-1.0, 51.0 + 150 / 110_540]],
    }
    lines = transform.overhead_lines([("UKPN", 33.0, north), ("UKPN", 132.0, crossing)], site, max_m=120)
    assert [(ln.voltage_kv, ln.crosses_site, ln.distance_m) for ln in lines] == [(132.0, True, 0), (33.0, False, 100)]
    assert transform.overhead_lines([("UKPN", 33.0, north)], site, max_m=50) == []


def test_transmission_queue():
    response = ckan.DatastoreSearchSqlResponse[neso.TecRegisterRecord].model_validate(load("neso_tec_at_sites_dorking"))
    queue = transform.transmission_projects(response.result.records, "NESO TEC")
    assert queue[0].capacity_mw == max(p.capacity_mw for p in queue)
    assert any(p.is_storage for p in queue) == any("Energy Storage" in (p.plant_type or "") for p in queue)


# --------------------------------------------- output ------------------------------------------- #


def test_without_geometry_is_prompt_sized(site):
    data = LocationData(
        coords=HERE,
        deterministic=Deterministic(
            designations=[
                Designation(
                    kind="sssi",
                    category="ecology",
                    on_site=True,
                    source="natural_england",
                    geometry=to_geometry(site.boundary),
                )
            ]
        ),
    )
    dumped = data.without_geometry()
    assert "geometry" not in dumped["deterministic"]["designations"][0]
    assert LocationData.model_validate(data.model_dump(mode="json")) == data  # survives a Temporal payload


@pytest.mark.parametrize(
    ("published", "voltages", "name", "expected"),
    [
        (11.0, [33.0], "Dorking Town 11kV", 11.0),  # the published connection voltage wins
        (None, [33.0, 11.0], "Crockerton Primary", 11.0),  # else the lowest published voltage
        (None, [], "Hockley 132/11Kv", 11.0),  # else the lowest voltage in the name
        (None, [], "St Pauls Bsp 132Kv", 132.0),
        (None, [], "Broadweir Primary", None),  # nothing published: the caller decides
    ],
)
def test_connection_kv(published, voltages, name, expected):
    assert transform._connection_kv(published, voltages, name) == expected  # ruff: ignore[private-member-access]


def test_npg_substations():
    records = npg.DATASETS["capacity_heatmap"].parse(load("npg_capacity_heatmap_leeds")).results
    subs = transform.npg_substations(records, Site(Coordinates(lat=53.7997, lon=-1.5492)))
    assert [s.name for s in subs] == ["Upper Basinghall Street", "Whitehall Road 2/3"]
    town = subs[0]
    assert (town.operator, town.kind, town.connection_voltage_kv) == ("Northern Powergrid", "primary", 11.0)
    assert town.gsp is None  # NPg publishes asset ids, not names
    assert town.headroom.generation_rag == "green"
    assert town.headroom.demand == pytest.approx(9.16)


def test_npg_limiting_factor_drops_the_colour():
    assert transform._limiting_factor("Red - Fault Level") == "Fault Level"  # ruff: ignore[private-member-access]
    assert transform._limiting_factor("Green") is None  # ruff: ignore[private-member-access]
