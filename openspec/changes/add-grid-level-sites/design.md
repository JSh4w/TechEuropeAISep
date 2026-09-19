## Context

`add-ukpn-capacity-proposal` caps primary proposals by voltage (8 MW up to 22 kV, 50 MW at 33 and 66 kV). This change adds a second tier for larger requests. It cannot be designed in detail until the dataset is chosen.

## Goals / Non-Goals

**Goals:** a second tier that reuses the snapshot, validation and `propose` structure.

**Non-Goals:** transmission-level sites.

## Decisions

### Chosen Dataset (Task 1.1 Decision)

- **Dataset Name / ID:** `grid-and-primary-sites` (UK Power Networks Grid and Primary Sites)
- **URL:** https://ukpowernetworks.opendatasoft.com/explore/dataset/grid-and-primary-sites/
- **Licence:** Creative Commons Attribution 4.0 International (CC BY 4.0)
- **Access / Download:** Opendatasoft Explore API v2.1 via `bessible.api.ukpn.DATASETS["substations"]` using `UKPN_API_KEY`. In the absence of a key or network, committed offline snapshot `data/ukpn/grid_substations.json` is loaded with full provenance recorded in `manifest.json`.

### Interfaces (confirmed against the chosen dataset)

```python
class GridSubstation(BaseModel):
    id: str
    name: str
    position: Position
    voltage_kv: Literal[132] = 132
    headroom_import_mw: float
    headroom_export_mw: float
    site_type: str = "Grid Substation"
    licence_area: str | None = None
    gsp: str | None = None
    bsp: str | None = None
    max_demand_mva: float | None = None
    firm_capacity_mva: float | None = None

def propose(position: Position, snapshot: Snapshot, run_id: str, *, flexible: bool, requested_mw: float | None = None) -> CapacityOutput
```

`propose` keeps its behaviour when `requested_mw` is `None` or within the primary cap. Above it, `propose` searches `snapshot.grid_substations` within 5 km, uses the same headroom, floor and distance rules with a 100 MW voltage cap, and labels the connection 132 kV.

**Why 100 MW:** the UKPN register's largest battery is 99.8 MW. It is a stand-in until the chosen dataset gives real limits.

**Why never fall back to primary:** a primary substation would give a proposal that cannot carry the size. An honest "no coverage" is better.

## Risks / Trade-offs

- [The chosen dataset is not in Opendatasoft form] → Resolved: `grid-and-primary-sites` is in standard UKPN Opendatasoft form, with schema aligned with `GridPrimarySite`.
- [Grid-level headroom means something different] → Headroom is derived from transformer firm capacity minus peak demand, with export headroom reflecting the firm transformer capacity.

## Open Questions

None (all resolved).
