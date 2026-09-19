## Why

The UKPN heatmap covers primary substations only (6.6 to 66 kV), so the tool stops at about 50 MW. UKPN's registered batteries have a median of 33 MW and a maximum of 99.8 MW, and 5 of 38 recorded projects are above 50 MW. Larger projects need a 132 kV or grid-level connection that no dataset in scope covers.

**Owner:** TBD.

## What Changes

Two features. F1 must finish before F2.

- **F1 grid-substation-data:** ingest a grid-level dataset covering grid substations and 132 kV into the snapshot, with the same validation and provenance as the primary data.
- **F2 large-site-capacity:** when the request's battery size exceeds what a primary substation can carry, propose a connection at a grid-level substation, labelled 132 kV, with a ceiling capped at 100 MW. When no grid-level data covers the site, say so instead of guessing.

## Capabilities

### New Capabilities

- `grid-level-capacity`: grid-level substation data and proposals for sites above the primary limit.

### Modified Capabilities

None.

## Impact

- `ukpn/models.py`, `ukpn/ingest.py`, `ukpn/snapshot.py`, `ukpn/capacity.py` extended; snapshot grows.
- `add-financial-model` already records the 132 kV cable rate (£1.25m to £2m per km) for this change to use.
- Depends on `add-ukpn-capacity-proposal`.

## Blockers

- **No grid-level dataset chosen.** The heatmap has no grid substations and no 132 kV. *Needs a decision:* which dataset covers them. Nothing in this change can start until task 1.1 is answered.

## Non-goals

- Transmission connections and sites above 100 MW.
- Any change to how primary-substation proposals work.
- Cost modelling (owned by `add-financial-model`).
