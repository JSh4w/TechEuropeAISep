## Why

UK Power Networks (UKPN) capacity data misleads if read at face value. Its Red/Amber/Green fields are utilisation bands, not connectable MW. Its headroom covers one direction at a time, but a battery needs import and export. It also ignores the connection queue. A deterministic, explainable proposal that corrects this is the strongest technical piece of the demo.

**Owner:** TBD. The pasted source proposal does not name one.

## What Changes

- Ingest a UKPN snapshot (EPN, LPN, SPN), committed so the demo needs no key or UKPN call.
- Add `propose_capacity`, a deterministic function (no LLM, under 1 s) that fills the skeleton's `capacity` stage:
  - Serving substation by **point-in-polygon** on distribution areas, not nearest.
  - **Effective headroom**: available capacity minus accepted connection offers, per direction; export adds reverse power flow.
  - **Seasonal** firm capacity; the constraining season is named.
  - A **range**: firm floor to curtailment-bearing ceiling.
  - Proposed size is `min(export, import)`; the binding direction is named.
  - **Connection voltage gates size**: 11 kV about 8 MW, 33 kV about 50 MW. Blank voltage is parsed from the substation name.
  - **5 MW viability floor.** With flexible connection off and firm below the floor, the result is not viable and hints at `--flexible`.
  - Distance-penalised ranking, steep past **1 km**; farther options are flagged marginal, not hidden.
  - Out-of-area postcodes get a clear result. Every check is logged.
- Add postcode → lat/long (postcodes.io, cached) to `resolve_location`.
- Show RAG values, parent grid supply point status and the Transmission Impact Assessment threshold as context artifacts only.

## Capabilities

### New Capabilities

- `ukpn-data-snapshot`: ingestion, storage, loading and provenance of UKPN data.
- `capacity-proposal`: the deterministic proposal described above.

### Modified Capabilities

None. It fills the skeleton's stage through the existing `CapacityOutput`; new fields are optional additions.

## Impact

- New `src/bessible/ukpn/` package, committed `data/ukpn/` snapshot, dependency `shapely`, env var `UKPN_API_KEY` (ingest only).
- Depends on `add-temporal-pipeline-skeleton` models.
- Outputs are screening estimates, not advice; the report says so.

## Non-goals

Each is its own change:
- Competition pressure, LTDS Table 2a, Gate 2 timescales, snapshot refresh: `add-grid-connection-context`.
- Curtailment cost, cable cost per km, Ofgem fee: `add-financial-model`.
- Map, INSPIRE overlay, size slider: `add-web-ui`. Footprint area: `add-footprint-sizing`.
- Link → postcode extraction: `add-link-location-extraction`.
- Grid-level (132 kV) sites above 50 MW: `add-grid-level-sites`.
