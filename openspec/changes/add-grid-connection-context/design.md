## Context

Extends `add-ukpn-capacity-proposal` (snapshot, `propose`, `CapacityOutput`) and fills the skeleton's `grid_connection` stage (`NodeInput → GridOutput`). Each feature touches different files, so they can be built in parallel.

## Goals / Non-Goals

**Goals:** four features, each independently mergeable and testable.

**Non-Goals:** changing the skeleton workflow or any model field type. Only optional fields are added.

## Decisions

### Feature boundaries

| Feature | New files | Touches |
|---|---|---|
| F1 | `ukpn/competition.py` | `ukpn/ingest.py` (Table 6), `stages/capacity.py` (artifacts) |
| F2 | `ukpn/export_ceiling.py` | `ukpn/ingest.py` (Table 2a), `ukpn/capacity.py` (ceiling line) |
| F3 | `ukpn/timescales.py` | `stages/grid.py` |
| F4 | `ukpn/refresh.py` | `ukpn/ingest.py` (`--refresh`), `cli.py` (warning), `stages/synthesis.py` (age line) |

`ukpn/ingest.py` is shared. Each feature adds its own fetch function and does not change the others'.

### Interfaces

```python
# F1
class Competition(BaseModel):
    offers_not_accepted_mw: float
    budget_estimates_mw: float
    enquiries_mw: float
    weighted_mw: float
    pressure: Literal["low", "medium", "high"]
def competition(sub: PrimarySubstation, snap: Snapshot) -> Competition
WEIGHTS = {"offers": 0.5, "budget": 0.25, "enquiries": 0.1}   # assumption, documented in the artifact

# F2
def export_ceiling(sub: PrimarySubstation, snap: Snapshot) -> float | None   # None = unavailable or not validated
def validate_export_ceiling(snap: Snapshot) -> list[str]                      # ids of failing substations

# F3
class GspQueue(BaseModel): projects: int; total_mw: float; by_status: dict[str, int]; next_position: int
class Timescales(BaseModel): p25_months: float; p75_months: float; median_months: float; records: int; low_confidence: bool
def gsp_queue(gsp_id: str, snap: Snapshot) -> GspQueue | None
def timescales(gsp_id: str, snap: Snapshot) -> Timescales | None

# F4
def refresh(dest: Path) -> DiffSummary      # builds in a temp dir, swaps atomically
def snapshot_age_days(snap: Snapshot, today: date) -> int
```

`CapacityOutput` gains optional `competition: Competition | None`, `export_ceiling_mw: float | None`. `GridOutput` already has the F3 fields.

### Weights and bands

The weights (0.5, 0.25, 0.1) and the pressure bands (0.5 and 1 times headroom) are assumptions. The source proposal only says "weighted below the firm queue". They are shown in the artifact claim so a reader can challenge them.

**Why context only:** subtracting weaker signals would make the firm figure unfalsifiable; the source proposal keeps the firm queue as the only subtraction.

### Export ceiling

The validation check reuses the Embedded Capacity Register: a substation with a registered battery must not get a ceiling below that battery. The check runs at ingest and writes `export_ceiling_validated: bool` plus failing ids to the manifest. `export_ceiling()` returns None unless the flag is true.

### Timescales

Records come from GSP Project Status (already in the snapshot). Months are the difference between application and offer dates where both exist. Quartiles use `statistics.quantiles`.

## Risks / Trade-offs

- [Table 2a field names or semantics differ from the source proposal] → F2 task 1 confirms them; if validation fails, F2 stays disabled and the ceiling falls back to import-side only.
- [Few records at a GSP] → Low-confidence flag, never a silent guess.
- [Refresh fails midway] → Temp folder plus swap.

## Open Questions

- Whether pressure should also be shown in MW terms in the report or only as a band.
- Whether a 6-month warning threshold is right for a heatmap published about twice a year.
