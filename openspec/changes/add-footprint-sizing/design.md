## Context

Pure calculation with no I/O, so it can be called from the CLI, the workflow's stages, and a later web API. The skeleton's `ConfirmedSite.footprint_geojson` is `None` until this exists.

## Goals / Non-Goals

**Goals:** one small module, three small features, nothing that blocks others.

**Non-Goals:** layout, orientation, real parcel shape.

## Decisions

### Interfaces

```python
ACRES_PER_MWH = (0.05, 0.075)
M2_PER_ACRE = 4046.8564224

def reserved_acres(capacity_mw: float, duration_h: int = 4) -> tuple[float, float]
def reserved_acres_by_duration(capacity_mw: float) -> dict[int, tuple[float, float]]   # 2, 4, 8
def footprint_polygon(center: Position, acres: float, aspect: float = 2.0) -> dict[str, Any]  # GeoJSON Polygon
```

`footprint_polygon` builds a rectangle in a local metric frame (equirectangular approximation about `center.lat`), then converts corners to lat/lon. That is accurate to well under 1% at these sizes.

### Where it runs

- The CLI computes the range and polygon while prompting, and sends the polygon in `SiteDecision.footprint_geojson` (optional field added to `SiteDecision`). The workflow copies it into `ConfirmedSite`.
- `stages/synthesis.py` calls `reserved_acres` on the confirmed capacity and writes `footprint.json` (inputs, range, rule of thumb source) to the run folder as the artifact's evidence.

**Why the CLI generates the polygon:** the workflow must stay deterministic and free of I/O; a pure function would also be safe there, but the web UI will need the same value while the user moves the footprint, so the client owns it.

**Why 4 h as default:** the source proposal leaves this open. 8 h never under-reserves but looks disproportionate; 2 h can under-reserve. 4 h is the middle, and the CLI also shows the range.

## Risks / Trade-offs

- [The rule of thumb is coarse] → Labelled planning-grade in every artifact.
- [Users read the 4 h area as the only answer] → 2 h and 8 h areas are printed beside it.

## Open Questions

- Whether the footprint aspect ratio should come from the title boundary shape later.
