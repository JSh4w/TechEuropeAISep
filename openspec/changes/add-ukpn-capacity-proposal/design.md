## Context

See proposal.md for motivation. This change fills the `capacity` stage defined in `add-temporal-pipeline-skeleton` (`CapacityInput` → `CapacityOutput`) and the postcode branch of `resolve_location`. Implementation of the skeleton's models comes first; this change may only ADD optional fields to them.

UKPN's Opendatasoft API blocks `/records` and returns headers only from `/exports/csv` without an API key, so ingestion needs `UKPN_API_KEY`. Field names below come from the source proposal and are confirmed at ingest time (task 1.2).

## Goals / Non-Goals

**Goals:**
- A pure, offline, sub-second function from position to capacity proposal.
- A committed snapshot, so teammates and the demo Mac need no key.

**Non-Goals:**
- A server, database, or cache layer. Data is read into memory at first use.
- Anything in the proposal's Non-goals.

## Decisions

### Layout

```
src/bessible/ukpn/
  models.py     # normalised snapshot models
  ingest.py     # `uv run python -m bessible.ukpn.ingest` (needs UKPN_API_KEY)
  snapshot.py   # load + validate + spatial index; `get_snapshot()` cached
  capacity.py   # pure `propose(...)`
  geocode.py    # postcodes.io client with JSON fixture cache
data/ukpn/      # committed: tables.json, areas.geojson, manifest.json
out/capacity_checks.jsonl   # append-only log (gitignored)
```

`stages/capacity.py` (skeleton) calls `propose` and wraps the result as `CapacityOutput` plus artifacts. `stages/location.py` calls `geocode_postcode` when the request has a postcode.

### Snapshot files

- `tables.json`: `{"manifest_ref": "manifest.json", "substations": [PrimarySubstation...], "ecr": [...], "gsp": [...], "gsp_projects": [...]}` validated into Pydantic models at load. JSON needs no extra dependency, and validation catches the source's type inconsistencies.
- `areas.geojson`: FeatureCollection, one polygon per primary, `properties.substation_id`. Simplified with shapely `simplify(tolerance)` chosen to give about 100 vertices.
- `manifest.json`: `{"fetched_at": "...", "datasets": {"<id>": {"rows": N}}}`.

**Why committed:** the API key is the only external prerequisite of the whole tool. Committing about 5 MB removes it from the demo path.

**Alternatives rejected:** SQLite or Postgres. The data is read-only and fits in memory.

### Models (`ukpn/models.py`)

```python
class PrimarySubstation(BaseModel):
    id: str
    name: str
    position: Position
    licence_area: Literal["EPN", "LPN", "SPN"]
    voltage_kv: float                       # parsed from name when blank
    gsp_id: str | None
    demand_available_mw: float              # import headroom at peak
    demand_firm_mw: float
    demand_min_mw: float                    # may be negative
    load_offers_accepted_mw: float
    gen_available_mw: float                 # export headroom
    gen_offers_accepted_mw: float
    reverse_power_available_mw: float
    firm_capacity_mw: dict[Literal["winter", "summer"], float]
    tia_threshold_mw: Literal[1, 5]
    rag_generation: str | None
    rag_demand: str | None

class Snapshot(BaseModel):                  # plus a non-serialised STRtree
    fetched_at: datetime
    substations: dict[str, PrimarySubstation]
    gsp: dict[str, GridSupplyPoint]
```

### Algorithm (`capacity.py`)

```python
def propose(position: Position, snapshot: Snapshot, *, flexible: bool) -> CapacityResult
```

1. Point-in-polygon with the STRtree. No hit → out of area (viable=False, message "Outside UKPN licence areas").
2. For each candidate (serving + up to 4 nearest others within 5 km):
   - `import_firm = demand_available - load_offers_accepted`
   - `export_firm = gen_available - gen_offers_accepted + (reverse_power_available if demand_min < 0 else 0)`
   - Seasonal: scale each direction by that season's `firm_capacity_mw` ratio; `firm = min over seasons and directions`; the argmin gives `binding_season` and `binding_direction`.
   - `import_ceiling = demand_firm - demand_min - load_offers_accepted`; `ceiling = max(firm, min(import_ceiling, voltage_cap))`.
   - `voltage_cap`: 8 MW for `voltage_kv <= 22`, 50 MW for 33 and 66 kV. Firm is also capped at `voltage_cap`.
   - `size = ceiling if flexible else firm`; viable if `size >= 5`.
3. Score: `size * f(d)`, `f(d) = 1 if d <= 1 else exp(-2 * (d - 1))`, `d` = haversine km to the substation. Marginal if `d > 1`. The serving substation is always the primary option (it is the predicted point of connection); alternates are ranked by score.
4. The result's `recommended_mw = size` of the serving substation. If that fails the floor, `message` states `firm` and `ceiling` and suggests `--flexible` (see spec). Alternates are listed in the artifacts.
5. Append one JSON line to `out/capacity_checks.jsonl`.

Artifacts: one per key figure, `model_used="ukpn-snapshot"`, `confidence=0.9`, `source_url` = dataset page on UKPN's open data portal, claim text includes the snapshot date. Separate context artifacts for RAG, the GSP status and the TIA threshold (claim states "context only, not used in the verdict").

### Additions to `CapacityOutput` (optional fields only)

```python
alternates: list[AlternateOption] = []     # substation, distance_km, size_mw, marginal
tia_threshold_mw: Literal[1, 5] | None = None
snapshot_date: date | None = None
```

### Geocoding

`geocode_postcode(pc: str) -> Position` calls `https://api.postcodes.io/postcodes/<pc>` with `httpx`, caching responses as `data/fixtures/postcodes/<normalised>.json`. Fixtures for the demo postcodes are committed. Add `httpx` to runtime dependencies.

## Risks / Trade-offs

- [The source's range formulas are demand-side only] → The ceiling uses the import-side formula and takes the smaller of it and the voltage cap; the export-side ceiling is an open question. The ceiling is documented as an assumption in the artifact claim.
- [Substation coordinates and polygons disagree] → Distance uses substation coordinates; containment uses polygons. Documented; only used for different decisions.
- [UKPN field names differ from the source proposal's] → Task 1.2 confirms them against the real datasets before any logic is written.
- [Voltage caps for 6.6, 22 and 66 kV are not in the source] → 22 kV and below use the 11 kV cap; 66 kV uses the 33 kV cap. Assumption, recorded in the artifact.
- [No UKPN key available] → Snapshot is committed; only re-ingest needs the key.
- [Few sites pass the floor] → Expected (only about 5.5% of the area is within 1 km of a primary). Demo pins are chosen from the fixtures; near misses show as marginal, not hidden.

## Open Questions

- Export-side ceiling formula, and whether Table 2a's `reverse_power_capability_percent` should feed it.
- Which postcodes are the demo pins (drives fixture selection).
- Whether the seasonal scaling matches how the distribution-area dataset publishes seasonal firm capacity (checked at ingest).
