## Why

A developer needs to know how much land the battery takes before acquiring it. Area tracks energy (MWh), not power (MW), so a single per-MW rule breaks across 2 h, 4 h and 8 h. This is small, pure, and useful in the CLI today. A map UI later reuses it.

**Owner:** TBD.

## What Changes

Three small features.

- **F1 footprint-area:** `reserved_acres(capacity_mw, duration_h)` at **0.05 to 0.075 acres per MWh**, derived from the rule of thumb of 0.1 to 0.15 acres per MW at 2 h. Planning-grade estimate, not a design figure.
- **F2 footprint-geometry:** generate a rectangular footprint polygon of the mid-range area, centred on a position, as GeoJSON.
- **F3 cli-footprint:** the CLI confirmation prompt shows the area for the chosen capacity and updates it when the capacity changes. The report states the reserved area with its evidence.

Which duration sizes the footprint? The map step runs before the duration comparison, so this change defaults to **4 h** and also shows the 2 h to 8 h range. Sizing for 8 h never under-reserves but looks large.

## Capabilities

### New Capabilities

- `footprint-sizing`: area per MWh, generated footprint, CLI display, report line.

### Modified Capabilities

None.

## Impact

- New `src/bessible/footprint.py`; small edits to `cli.py` and `stages/synthesis.py`.
- `SiteDecision` and `ConfirmedSite` already allow a footprint; this change fills `footprint_geojson` (optional field, added if absent).
- No new dependencies.

## Non-goals

- The map, drag to position, and the size slider (`add-web-ui`).
- INSPIRE parcel overlay (`add-web-ui`).
- Site layout or design-grade area.
