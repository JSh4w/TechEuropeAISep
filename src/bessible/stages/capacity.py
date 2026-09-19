"""Grid capacity proposal from the UKPN snapshot: headroom per direction, voltage cap, range, 5 MW floor."""

from __future__ import annotations

import asyncio
import json
import math
import re
from operator import itemgetter
from typing import TYPE_CHECKING, Literal

from pydantic import HttpUrl

from bessible.config import settings
from bessible.models import AlternateOption, Artifact, CapacityInput, CapacityOutput, Position
from bessible.ukpn.snapshot import (
    DATASET_ID,
    DATASET_URL,
    GRID_DATASET_ID,
    GRID_DATASET_URL,
    Snapshot,
    get_snapshot,
)

if TYPE_CHECKING:
    from bessible.api.ukpn import CapacityHeatmapSite

MODEL_USED = "ukpn-snapshot"
CONFIDENCE = 0.9
FLOOR_MW = 5.0
SEARCH_RADIUS_KM = 5.0  # serving substation and alternates must be within this
MARGINAL_KM = 1.0
MAX_ALTERNATES = 4
LOW_VOLTAGE_CAP_MW = 8.0  # 22 kV and below
HIGH_VOLTAGE_CAP_MW = 50.0  # 33 kV and 66 kV
GRID_VOLTAGE_CAP_MW = 100.0  # 132 kV
EARTH_RADIUS_KM = 6371.0088
CHECK_LOG = "capacity_checks.jsonl"

_VOLTAGE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*kv", re.IGNORECASE)
_TIA_RE = re.compile(r"\(TIA\).*?=\s*(\d+)\s*MW", re.IGNORECASE)


def haversine_km(a: Position, lat: float, lon: float) -> float:
    """Great-circle distance in km from `a` to a WGS84 point."""
    p1, p2 = math.radians(a.lat), math.radians(lat)
    dphi, dlmb = p2 - p1, math.radians(lon - a.lon)
    h = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(h))


def connection_voltage_kv(row: CapacityHeatmapSite) -> float | None:
    """Proposed connection voltage; falls back to the row's own voltage, then the name ("Dorking Town 11kV")."""
    if row.voltage:
        return row.voltage
    if row.voltages:
        return row.voltages
    match = _VOLTAGE_RE.search(row.name or "")
    return float(match.group(1)) if match else None


def voltage_cap_mw(voltage_kv: float) -> float:
    """What the connection voltage can carry, independent of headroom."""
    return LOW_VOLTAGE_CAP_MW if voltage_kv <= 22 else HIGH_VOLTAGE_CAP_MW


def tia_threshold_mw(row: CapacityHeatmapSite) -> Literal[1, 5] | None:
    """Transmission Impact Assessment threshold (1 or 5 MW) parsed from the row description."""
    match = _TIA_RE.search(row.description or "")
    value = match.group(1) if match else None
    if value == "1":
        return 1
    return 5 if value == "5" else None


def distance_weight(distance_km: float) -> float:
    """1 up to 1 km, then falling steeply: exp(-2 * (d - 1))."""
    return 1.0 if distance_km <= MARGINAL_KM else math.exp(-2 * (distance_km - MARGINAL_KM))


class Headroom:
    """Effective headroom of one primary substation. All values in MW."""

    def __init__(self, row: CapacityHeatmapSite, *, flexible: bool) -> None:
        """Compute import/export headroom net of accepted offers, then firm, ceiling and size."""
        voltage = connection_voltage_kv(row)
        if voltage is None:
            msg = f"Cannot determine connection voltage for substation '{row.name}'"
            raise ValueError(msg)
        self.row = row
        self.voltage_kv = voltage
        self.cap_mw = voltage_cap_mw(voltage)
        load_accepted = row.loadconnectionoffersacceptedcapacity or 0.0
        gen_accepted = row.generationconnectionoffersacceptedcapacity or 0.0
        reverse = (row.reversepowerflowavailablecapacity or 0.0) if (row.demandminimum or 0.0) < 0 else 0.0
        self.import_mw = max(0.0, (row.demandavailablecapacity or 0.0) - load_accepted)
        self.export_mw = max(0.0, (row.generationavailablecapacity or 0.0) - gen_accepted + reverse)
        self.binding_direction: Literal["import", "export"] = "import" if self.import_mw <= self.export_mw else "export"
        self.firm_mw = min(self.import_mw, self.export_mw, self.cap_mw)
        import_ceiling = (row.demandfirmcapacity or 0.0) - (row.demandminimum or 0.0) - load_accepted
        self.ceiling_mw = max(self.firm_mw, min(import_ceiling, self.cap_mw))
        self.size_mw = self.ceiling_mw if flexible else self.firm_mw


def _viable_message(head: Headroom, *, flexible: bool) -> str | None:
    """Explain why a site fails the 5 MW floor, or None if it passes."""
    if head.size_mw >= FLOOR_MW:
        return None
    name = head.row.name
    if not flexible and head.ceiling_mw >= FLOOR_MW:
        return (
            f"Firm capacity at {name} is {head.firm_mw:.1f} MW (below the {FLOOR_MW:g} MW floor); "
            f"ceiling is {head.ceiling_mw:.1f} MW. Enable flexible connection (--flexible) to use the ceiling."
        )
    return (
        f"Ceiling capacity at {name} is {head.ceiling_mw:.1f} MW, below the {FLOOR_MW:g} MW floor; "
        f"firm capacity is {head.firm_mw:.1f} MW."
    )


def _artifact(
    run_id: str,
    suffix: str,
    claim: str,
    snapshot: Snapshot,
    confidence: float = CONFIDENCE,
    dataset_id: str = DATASET_ID,
    dataset_url: str = DATASET_URL,
) -> Artifact:
    return Artifact(
        id=f"capacity-{suffix}-{run_id[:8]}",
        stage="capacity",
        claim=f"{claim} [{dataset_id}, snapshot {snapshot.fetched_at.isoformat()}]",
        source_url=HttpUrl(dataset_url),
        confidence=confidence,
        model_used=MODEL_USED,
    )


def _alternates(nearby: list[tuple[float, CapacityHeatmapSite]], *, flexible: bool) -> list[AlternateOption]:
    """Up to four other primaries within range, best distance-weighted size first. Far ones are flagged, not hidden."""
    scored: list[tuple[float, AlternateOption]] = []
    for d, row in nearby[1 : MAX_ALTERNATES + 1]:
        alt = Headroom(row, flexible=flexible)
        option = AlternateOption(
            substation=row.name or "", distance_km=round(d, 2), size_mw=round(alt.size_mw, 2), marginal=d > MARGINAL_KM
        )
        scored.append((alt.size_mw * distance_weight(d), option))
    return [opt for _, opt in sorted(scored, key=lambda t: -t[0])]


def _artifacts(run_id: str, snapshot: Snapshot, head: Headroom, dist: float) -> list[Artifact]:
    """One artifact per key figure, plus a context-only artifact for RAG, parent GSP and TIA."""
    row = head.row
    tia = tia_threshold_mw(row)
    marginal_note = f"; {dist:.1f} km away, marginal beyond {MARGINAL_KM:g} km" if dist > MARGINAL_KM else ""
    return [
        _artifact(
            run_id,
            "substation",
            f"Predicted point of connection: {row.name} ({head.voltage_kv:g} kV), "
            f"{dist:.2f} km away{marginal_note}. "
            "Nearest primary substation by distance (distribution-area polygons not in the snapshot)",
            snapshot,
        ),
        _artifact(
            run_id,
            "headroom",
            f"Effective headroom at {row.name}: import {head.import_mw:.1f} MW, export {head.export_mw:.1f} MW "
            "(available capacity minus accepted offers; export adds reverse power flow "
            "when minimum demand is negative)",
            snapshot,
        ),
        _artifact(
            run_id,
            "range",
            f"Firm {head.firm_mw:.1f} MW, ceiling {head.ceiling_mw:.1f} MW, limited by {head.binding_direction}; "
            f"{head.voltage_kv:g} kV caps size at {head.cap_mw:g} MW. Ceiling = import-side formula "
            "(demand firm capacity - minimum demand - accepted load offers), an assumption. "
            "No seasonal split in this dataset",
            snapshot,
        ),
        _artifact(
            run_id,
            "context",
            f"Context only, not used in the verdict: RAG demand {row.demandconstraint}, "
            f"generation {row.generationconstraint}; parent GSP {row.gsp or 'unknown'}; "
            f"TIA threshold {tia if tia is not None else 'unknown'} MW",
            snapshot,
        ),
    ]


def _propose_grid_level(
    position: Position,
    snapshot: Snapshot,
    run_id: str,
    *,
    flexible: bool,
    requested_mw: float,
) -> CapacityOutput:
    """Proposal logic when requested size exceeds the primary voltage cap (>50 MW)."""
    if requested_mw > GRID_VOLTAGE_CAP_MW:
        msg = (
            f"Requested battery size ({requested_mw:g} MW) exceeds maximum grid-level capacity ({GRID_VOLTAGE_CAP_MW:g} MW); "
            "sites above 100 MW are out of scope"
        )
        return CapacityOutput(
            viable=False,
            message=msg,
            out_of_area=False,
            snapshot_date=snapshot.fetched_at,
            artifacts=[
                _artifact(
                    run_id,
                    "scope",
                    f"Out of scope: {msg}",
                    snapshot,
                    confidence=1.0,
                    dataset_id=GRID_DATASET_ID,
                    dataset_url=GRID_DATASET_URL,
                )
            ],
        )

    grid_subs = [
        g
        for g in snapshot.grid_substations
        if g.position is not None and g.position.lat is not None and g.position.lon is not None
    ]
    ranked = sorted(
        ((haversine_km(position, g.position.lat, g.position.lon), g) for g in grid_subs),
        key=itemgetter(0),
    )
    nearby = [(d, g) for d, g in ranked if d <= SEARCH_RADIUS_KM]
    if not nearby:
        msg = (
            f"No UK Power Networks grid-level substation within {SEARCH_RADIUS_KM:g} km in the snapshot; "
            "no grid-level data covers the site"
        )
        return CapacityOutput(
            viable=False,
            message=msg,
            out_of_area=True,
            snapshot_date=snapshot.fetched_at,
            artifacts=[
                _artifact(
                    run_id,
                    "area",
                    f"No grid-level coverage: {msg}",
                    snapshot,
                    confidence=0.8,
                    dataset_id=GRID_DATASET_ID,
                    dataset_url=GRID_DATASET_URL,
                )
            ],
        )

    dist, serving = nearby[0]
    import_mw = serving.headroom_import_mw
    export_mw = serving.headroom_export_mw
    binding_direction: Literal["import", "export"] = "import" if import_mw <= export_mw else "export"
    firm_mw = min(import_mw, export_mw, GRID_VOLTAGE_CAP_MW)
    ceiling_mw = max(firm_mw, min(import_mw, GRID_VOLTAGE_CAP_MW))
    size_mw = ceiling_mw if flexible else firm_mw

    if size_mw < FLOOR_MW:
        if not flexible and ceiling_mw >= FLOOR_MW:
            msg = (
                f"Firm capacity at {serving.name} is {firm_mw:.1f} MW (below the {FLOOR_MW:g} MW floor); "
                f"ceiling is {ceiling_mw:.1f} MW. Enable flexible connection (--flexible) to use the ceiling."
            )
        else:
            msg = (
                f"Ceiling capacity at {serving.name} is {ceiling_mw:.1f} MW, below the {FLOOR_MW:g} MW floor; "
                f"firm capacity is {firm_mw:.1f} MW."
            )
        viable = False
    else:
        viable = True
        msg = None

    scored_alts: list[tuple[float, AlternateOption]] = []
    for d, g in nearby[1 : MAX_ALTERNATES + 1]:
        alt_firm = min(g.headroom_import_mw, g.headroom_export_mw, GRID_VOLTAGE_CAP_MW)
        alt_ceiling = max(alt_firm, min(g.headroom_import_mw, GRID_VOLTAGE_CAP_MW))
        alt_size = alt_ceiling if flexible else alt_firm
        opt = AlternateOption(
            substation=g.name,
            distance_km=round(d, 2),
            size_mw=round(alt_size, 2),
            marginal=d > MARGINAL_KM,
        )
        scored_alts.append((alt_size * distance_weight(d), opt))
    alternates = [opt for _, opt in sorted(scored_alts, key=lambda t: -t[0])]

    marginal_note = f"; {dist:.1f} km away, marginal beyond {MARGINAL_KM:g} km" if dist > MARGINAL_KM else ""
    artifacts = [
        _artifact(
            run_id,
            "substation",
            f"Predicted point of connection: {serving.name} (132 kV), "
            f"{dist:.2f} km away{marginal_note}. "
            "Grid-level substation connection for large request (>50 MW)",
            snapshot,
            dataset_id=GRID_DATASET_ID,
            dataset_url=GRID_DATASET_URL,
        ),
        _artifact(
            run_id,
            "headroom",
            f"Effective headroom at {serving.name}: import {import_mw:.1f} MW, export {export_mw:.1f} MW",
            snapshot,
            dataset_id=GRID_DATASET_ID,
            dataset_url=GRID_DATASET_URL,
        ),
        _artifact(
            run_id,
            "range",
            f"Firm {firm_mw:.1f} MW, ceiling {ceiling_mw:.1f} MW, limited by {binding_direction}; "
            f"132 kV connection capped at {GRID_VOLTAGE_CAP_MW:g} MW",
            snapshot,
            dataset_id=GRID_DATASET_ID,
            dataset_url=GRID_DATASET_URL,
        ),
        _artifact(
            run_id,
            "context",
            f"Context only, not used in the verdict: licence area {serving.licence_area or 'unknown'}; "
            f"parent GSP {serving.gsp or 'unknown'}; Bulk Supply Point {serving.bsp or 'unknown'}",
            snapshot,
            dataset_id=GRID_DATASET_ID,
            dataset_url=GRID_DATASET_URL,
        ),
    ]

    return CapacityOutput(
        viable=viable,
        message=msg,
        out_of_area=False,
        substation=serving.name,
        connection_voltage_kv=132.0,
        firm_mw=firm_mw,
        ceiling_mw=ceiling_mw,
        recommended_mw=size_mw,
        binding_direction=binding_direction,
        binding_season=None,
        distance_km=round(dist, 2),
        alternates=alternates,
        tia_threshold_mw=None,
        snapshot_date=snapshot.fetched_at,
        artifacts=artifacts,
    )


def propose(
    position: Position,
    snapshot: Snapshot,
    run_id: str,
    *,
    flexible: bool,
    requested_mw: float | None = None,
) -> CapacityOutput:
    """Deterministic capacity proposal for a position. Pure: no I/O, no clock."""
    if requested_mw is not None and requested_mw > HIGH_VOLTAGE_CAP_MW:
        return _propose_grid_level(position, snapshot, run_id, flexible=flexible, requested_mw=requested_mw)

    primaries = [
        r for r in snapshot.substations if r.type == "Primary" and r.latitude is not None and r.longitude is not None
    ]
    ranked = sorted(
        ((haversine_km(position, r.latitude, r.longitude), r) for r in primaries),  # type: ignore[arg-type]
        key=itemgetter(0),
    )
    nearby = [(d, r) for d, r in ranked if d <= SEARCH_RADIUS_KM]
    if not nearby:
        coverage = "partial demo snapshot" if snapshot.partial else "snapshot"
        msg = (
            f"No UK Power Networks primary substation within {SEARCH_RADIUS_KM:g} km in the {coverage} "
            f"({snapshot.fetched_at.isoformat()}); this tool covers UKPN areas "
            "(London, South East, East of England) only"
        )
        return CapacityOutput(
            viable=False,
            message=msg,
            out_of_area=True,
            snapshot_date=snapshot.fetched_at,
            artifacts=[_artifact(run_id, "area", f"Outside UKPN coverage: {msg}", snapshot, confidence=0.8)],
        )

    dist, serving_row = nearby[0]  # nearest primary; distribution-area polygons are not in the snapshot yet
    head = Headroom(serving_row, flexible=flexible)
    message = _viable_message(head, flexible=flexible)

    alternates = _alternates(nearby, flexible=flexible)

    return CapacityOutput(
        viable=message is None,
        message=message,
        out_of_area=False,
        substation=serving_row.name,
        connection_voltage_kv=head.voltage_kv,
        firm_mw=head.firm_mw,
        ceiling_mw=head.ceiling_mw,
        recommended_mw=head.size_mw,
        binding_direction=head.binding_direction,
        binding_season=None,
        distance_km=round(dist, 2),
        alternates=alternates,
        tia_threshold_mw=tia_threshold_mw(serving_row),
        snapshot_date=snapshot.fetched_at,
        artifacts=_artifacts(run_id, snapshot, head, dist),
    )


def _append_check_log(inp: CapacityInput, out: CapacityOutput) -> None:
    """Append one JSON line per check to ``out/capacity_checks.jsonl`` (write-only; never read in a run)."""
    record = {
        "run_id": inp.run_id,
        "postcode": inp.location.postcode,
        "position": inp.location.position.model_dump(),
        "flexible": inp.request.flexible_connection,
        "snapshot_date": out.snapshot_date.isoformat() if out.snapshot_date else None,
        "result": out.model_dump(mode="json", exclude={"artifacts"}),
    }
    path = settings.data_dir.parent / "out" / CHECK_LOG
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as fh:
        fh.write(json.dumps(record) + "\n")


async def propose_capacity(inp: CapacityInput) -> CapacityOutput:
    """Assess available grid headroom at the located position and propose capacity limits."""
    snapshot = await asyncio.to_thread(get_snapshot)
    out = propose(
        inp.location.position,
        snapshot,
        inp.run_id,
        flexible=inp.request.flexible_connection,
        requested_mw=inp.request.battery_mw,
    )
    await asyncio.to_thread(_append_check_log, inp, out)
    return out
