from __future__ import annotations

from datetime import date

import pytest

from bessible.api.ukpn import CapacityHeatmapSite
from bessible.models import Position
from bessible.stages.capacity import (
    connection_voltage_kv,
    distance_weight,
    haversine_km,
    propose,
    tia_threshold_mw,
)
from bessible.ukpn.models import GridSubstation
from bessible.ukpn.snapshot import Snapshot, load_snapshot

SITE = Position(lat=51.5, lon=-0.5)


def row(name: str = "Test 33kV", lat: float = 51.5, lon: float = -0.5, **kw) -> CapacityHeatmapSite:
    base = {
        "name": name,
        "type": "Primary",
        "latitude": lat,
        "longitude": lon,
        "voltage": 33.0,
        "demandavailablecapacity": 20.0,
        "demandfirmcapacity": 40.0,
        "demandminimum": 2.0,
        "generationavailablecapacity": 20.0,
        "reversepowerflowavailablecapacity": 0.0,
        "demandconstraint": "GREEN",
        "generationconstraint": "GREEN",
    }
    return CapacityHeatmapSite.model_validate(base | kw)


def snap(*rows: CapacityHeatmapSite) -> Snapshot:
    return Snapshot(fetched_at=date(2026, 9, 1), partial=False, substations=list(rows))


def run(*rows: CapacityHeatmapSite, flexible: bool = False, position: Position = SITE):
    return propose(position, snap(*rows), "run-1234", flexible=flexible)


def test_queue_is_subtracted_from_import():
    out = run(
        row(demandavailablecapacity=20.0, loadconnectionoffersacceptedcapacity=8.0, generationavailablecapacity=30.0)
    )
    assert out.firm_mw == 12.0
    assert out.binding_direction == "import"


def test_export_binds_and_reverse_power_added_only_when_min_demand_negative():
    kw = {"generationavailablecapacity": 6.0, "reversepowerflowavailablecapacity": 3.0}
    positive_min = run(row(demandminimum=2.0, **kw))
    assert (positive_min.firm_mw, positive_min.binding_direction) == (6.0, "export")
    negative_min = run(row(demandminimum=-1.0, **kw))
    assert negative_min.firm_mw == 9.0
    assert negative_min.binding_direction == "export"  # 6 + 3 = 9 MW still below import 20 MW


def test_export_binding_direction_named():
    out = run(row(generationavailablecapacity=6.0))
    assert out.binding_direction == "export"
    assert out.firm_mw == 6.0


def test_voltage_caps_size_regardless_of_headroom():
    out = run(row(name="Big 11kV", voltage=11.0, demandavailablecapacity=30.0, generationavailablecapacity=30.0))
    assert out.firm_mw == 8.0
    assert out.ceiling_mw <= 8.0
    assert (
        run(
            row(voltage=33.0, demandavailablecapacity=80.0, generationavailablecapacity=80.0, demandfirmcapacity=200.0)
        ).firm_mw
        == 50.0
    )


def test_below_floor_hints_flexible_and_flexible_passes():
    r = row(demandavailablecapacity=3.0, demandfirmcapacity=15.0, demandminimum=2.0)  # firm 3, ceiling 13
    off = run(r, flexible=False)
    assert off.viable is False
    assert off.firm_mw == 3.0
    assert off.ceiling_mw == 13.0
    assert off.message is not None
    assert "3.0 MW" in off.message
    assert "13.0 MW" in off.message
    assert "--flexible" in off.message
    on = run(r, flexible=True)
    assert on.viable is True
    assert on.recommended_mw == 13.0


def test_ceiling_below_floor_not_viable_even_flexible():
    r = row(demandavailablecapacity=1.0, demandfirmcapacity=6.0, demandminimum=2.0)  # ceiling 4
    for flexible in (False, True):
        out = run(r, flexible=flexible)
        assert out.viable is False
        assert out.ceiling_mw == 4.0
        assert out.message is not None


def test_ceiling_is_never_below_firm():
    out = run(row(demandavailablecapacity=20.0, demandfirmcapacity=5.0, demandminimum=4.0))
    assert out.ceiling_mw >= out.firm_mw


def test_out_of_area():
    out = run(row(), position=Position(lat=53.4808, lon=-2.2426))
    assert out.out_of_area is True
    assert out.viable is False
    assert out.substation is None
    assert out.firm_mw == 0.0
    assert out.message is not None
    assert "UKPN" in out.message


def test_alternates_ranked_and_far_ones_flagged_marginal():
    near = row("Near 33kV")
    far = row("Far 33kV", lat=51.5 + 3 / 111.2)  # ~3 km north
    out = run(near, far)
    assert out.substation == "Near 33kV"
    assert [(a.substation, a.marginal) for a in out.alternates] == [("Far 33kV", True)]
    assert out.alternates[0].distance_km == pytest.approx(3.0, abs=0.1)


def test_serving_is_nearest_even_if_alternate_has_more_headroom():
    out = run(
        row("Near 33kV", demandavailablecapacity=6.0),
        row("Rich 33kV", lat=51.5 + 0.5 / 111.2, demandavailablecapacity=40.0),
        position=Position(lat=51.5 - 0.1 / 111.2, lon=-0.5),
    )
    assert out.substation == "Near 33kV"


def test_rag_is_context_only():
    green = run(row(demandconstraint="GREEN", generationconstraint="GREEN"))
    red = run(row(demandconstraint="RED", generationconstraint="RED"))
    assert green.model_dump(exclude={"artifacts"}) == red.model_dump(exclude={"artifacts"})
    ctx = next(a for a in red.artifacts if a.id.startswith("capacity-context"))
    assert "Context only" in ctx.claim
    assert "RED" in ctx.claim


def test_artifacts_cite_dataset_and_snapshot_date():
    out = run(row())
    assert len(out.artifacts) >= 4
    for a in out.artifacts:
        assert "ukpn-capacity-heatmap" in a.claim
        assert "2026-09-01" in a.claim
        assert a.model_used == "ukpn-snapshot"
        assert a.source_url is not None


def test_tia_threshold_parsed_from_description():
    assert (
        tia_threshold_mw(
            row(description="Transmission Impact assessment threshold (TIA) for generation at this site = 1  MW.")
        )
        == 1
    )
    assert tia_threshold_mw(row(description="(TIA) for generation at this site = 5 MW.")) == 5
    assert tia_threshold_mw(row(description=None)) is None
    assert run(row(description="(TIA) threshold = 5 MW")).tia_threshold_mw == 5


def test_voltage_parsed_from_name_when_missing():
    assert connection_voltage_kv(row("Dorking Town 11kV", voltage=None, voltages=None)) == 11.0
    assert connection_voltage_kv(row("No voltage here", voltage=None, voltages=None)) is None
    with pytest.raises(ValueError, match="connection voltage"):
        run(row("No voltage here", voltage=None, voltages=None))


def test_distance_helpers():
    assert distance_weight(0.5) == 1.0
    assert distance_weight(1.0) == 1.0
    assert 0 < distance_weight(3.0) < distance_weight(2.0) < 1.0
    assert haversine_km(SITE, 51.5 + 1 / 111.2, -0.5) == pytest.approx(1.0, abs=0.01)


def grid_row(
    name: str = "Test Grid 132kV",
    lat: float = 51.5,
    lon: float = -0.5,
    import_mw: float = 85.0,
    export_mw: float = 95.0,
    **kw,
) -> GridSubstation:
    base = {
        "id": "SPN-TEST-132",
        "name": name,
        "position": {"lat": lat, "lon": lon},
        "voltage_kv": 132,
        "headroom_import_mw": import_mw,
        "headroom_export_mw": export_mw,
        "site_type": "Grid Substation",
        "licence_area": "South Eastern Power Networks (SPN)",
    }
    return GridSubstation.model_validate(base | kw)


def test_snapshot_loads_grid_substations():
    snapshot = load_snapshot()
    assert len(snapshot.grid_substations) > 0
    for g in snapshot.grid_substations:
        assert g.voltage_kv == 132
        assert g.name
        assert g.position.lat is not None


def test_grid_level_request_80mw():
    snap = Snapshot(
        fetched_at=date(2026, 9, 1),
        partial=False,
        substations=[row()],
        grid_substations=[grid_row(name="Leatherhead 132kV", import_mw=85.0, export_mw=95.0)],
    )
    out = propose(SITE, snap, "run-80mw", flexible=False, requested_mw=80.0)
    assert out.viable is True
    assert out.substation == "Leatherhead 132kV"
    assert out.connection_voltage_kv == 132.0
    assert out.firm_mw == 85.0
    assert out.ceiling_mw <= 100.0
    assert any("132 kV" in a.claim for a in out.artifacts)
    assert any("grid-and-primary-sites" in a.claim for a in out.artifacts)


def test_grid_level_request_above_cap_150mw():
    snap = Snapshot(
        fetched_at=date(2026, 9, 1),
        partial=False,
        substations=[row()],
        grid_substations=[grid_row()],
    )
    out = propose(SITE, snap, "run-150mw", flexible=False, requested_mw=150.0)
    assert out.viable is False
    assert out.message is not None
    assert "100 MW" in out.message or "100" in out.message
    assert "out of scope" in out.message.lower()


def test_grid_level_no_coverage():
    snap = Snapshot(
        fetched_at=date(2026, 9, 1),
        partial=False,
        substations=[row(lat=53.48, lon=-2.24)],  # primary nearby
        grid_substations=[grid_row(lat=51.5, lon=-0.5)],  # grid far away (~250 km)
    )
    out = propose(Position(lat=53.48, lon=-2.24), snap, "run-no-cov", flexible=False, requested_mw=80.0)
    assert out.viable is False
    assert out.message is not None
    assert "no grid-level data covers the site" in out.message.lower()
    # verify no fallback to primary
    assert out.connection_voltage_kv != 33.0
    assert out.substation is None


def test_small_request_20mw_unchanged():
    snap = Snapshot(
        fetched_at=date(2026, 9, 1),
        partial=False,
        substations=[row(name="Serving 33kV", voltage=33.0)],
        grid_substations=[grid_row(name="Serving 132kV")],
    )
    out_default = propose(SITE, snap, "run-def", flexible=False, requested_mw=None)
    out_20mw = propose(SITE, snap, "run-20", flexible=False, requested_mw=20.0)
    assert out_20mw.substation == out_default.substation == "Serving 33kV"
    assert out_20mw.connection_voltage_kv == out_default.connection_voltage_kv == 33.0
    assert out_20mw.firm_mw == out_default.firm_mw
