## Context

`add-ukpn-capacity-proposal` caps primary proposals by voltage (8 MW up to 22 kV, 50 MW at 33 and 66 kV). This change adds a second tier for larger requests. It cannot be designed in detail until the dataset is chosen.

## Goals / Non-Goals

**Goals:** a second tier that reuses the snapshot, validation and `propose` structure.

**Non-Goals:** transmission-level sites.

## Decisions

### Interfaces (fields to be confirmed against the chosen dataset)

```python
class GridSubstation(BaseModel):
    id: str; name: str; position: Position
    voltage_kv: Literal[132]
    headroom_import_mw: float; headroom_export_mw: float
    # more fields follow the dataset's columns

def propose(position, snapshot, *, flexible: bool, requested_mw: float | None = None) -> CapacityResult
```

`propose` keeps its behaviour when `requested_mw` is `None` or within the primary cap. Above it, `propose` searches `snapshot.grid_substations` within 5 km, uses the same headroom, floor and distance rules with a 100 MW voltage cap, and labels the connection 132 kV.

**Why 100 MW:** the UKPN register's largest battery is 99.8 MW. It is a stand-in until the chosen dataset gives real limits.

**Why never fall back to primary:** a primary substation would give a proposal that cannot carry the size. An honest "no coverage" is better.

## Risks / Trade-offs

- [The chosen dataset is not in Opendatasoft form] → F1 task 1.2 confirms format before any design detail is fixed.
- [Grid-level headroom means something different] → The artifact states the dataset's own definition.

## Open Questions

- Which dataset covers grid substations and 132 kV (task 1.1).
