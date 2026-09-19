## Why

The capacity proposal answers "how many MW". A developer also needs to know how crowded the queue is, how solid the export side is, how long a connection takes, and how old the data is. Each of these is a separate feature that can be built and merged alone.

**Owner:** TBD. Same person as `add-ukpn-capacity-proposal` is best, because they share the snapshot.

## What Changes

Four independent features. Each starts once `add-ukpn-capacity-proposal` is merged.

- **F1 connection-competition:** report offers made but not accepted, budget estimates, and LTDS Table 6 enquiries as competing MW, weighted below the firm queue. Context only; never subtracted from headroom.
- **F2 export-ceiling:** use LTDS Table 2a (reverse power capability, seasonal transformer ratings) to compute the export-side ceiling. This replaces the demand-side-only ceiling.
- **F3 gate2-timescales:** real `grid_connection` stage. Gate 2 queue position at the parent grid supply point, and indicative connection timescales from modification-application outcomes.
- **F4 snapshot-refresh:** `ingest --refresh` with a diff summary, snapshot age in the report, and a warning when the snapshot is over 6 months old.
- Add a caveat artifact: effective headroom subtracts today's queue, which may shrink if the proposed Ofgem fee flushes speculative projects.

## Capabilities

### New Capabilities

- `connection-competition`: competing demand reported apart from the firm queue.
- `export-ceiling`: export-side ceiling from Table 2a, with a validation gate.
- `gate2-timescales`: parent GSP queue position and indicative timescales.
- `snapshot-refresh`: atomic refresh, diff summary, age warning.

### Modified Capabilities

None.

## Impact

- `data/ukpn/tables.json` gains Table 6 and Table 2a datasets; `ukpn/ingest.py` fetches them.
- `stages/grid.py` becomes real; `CapacityOutput` gains optional fields only.
- Depends on `add-ukpn-capacity-proposal`.

## Non-goals

- A numeric model of queue attrition. This change only adds the caveat.
- 132 kV sites (`add-grid-level-sites`).
- Scheduled or automatic refresh.
