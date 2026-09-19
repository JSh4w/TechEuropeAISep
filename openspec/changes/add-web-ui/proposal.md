## Why

The CLI works first, but a web map is the strongest demo visual: the user sees ranked substations, places a generated footprint, and watches the agents work live. The CLI stays as the fallback.

**Owner:** TBD.

## What Changes

Four features. F1 first; F2, F3 and F4 each build on F1 but not on each other.

- **F1 web-api:** FastAPI over the same Temporal client: start a run, read status and result, send the site decision, and run a direct capacity check (under 1 s, outside the workflow).
- **F2 live-trace:** stream progress to the browser over SSE from an append-only event log per run. Reconnect resumes from `Last-Event-ID`. No Redis. Logfire spans stay separate and never block or fail a run.
- **F3 site-map:** Next.js map with ranked substations and their effective headroom, a generated footprint the user positions (the user does not draw), an INSPIRE parcel overlay where available, and a size slider (5 MW to firm; to the ceiling when flexible connection is on). The flexible toggle defaults off and travels in the decision. Moving the pin re-checks capacity.
- **F4 web-report:** report page with every figure showing its source and snapshot date, and a screening-estimate notice.
- Two small skeleton additions, owned by Josh: an optional `flexible_connection` on `SiteDecision`, and re-running `propose_capacity` when the confirmed position moves.

## Capabilities

### New Capabilities

- `web-api`: HTTP interface to runs and the direct capacity check.
- `live-trace`: event log and SSE stream.
- `site-map`: map, footprint, slider, toggle and pin re-check.
- `web-report`: report page with provenance.

### Modified Capabilities

None.

## Impact

- New `src/bessible/api/`, `src/bessible/events.py`, and `web/` (Next.js). New dependencies: `fastapi`, `uvicorn`, a map library (MapLibre GL).
- Depends on the skeleton, `add-ukpn-capacity-proposal`, and `add-footprint-sizing`.
- External calls from the browser or backend: map tiles, HM Land Registry INSPIRE. Demo needs cached fixtures.

## Non-goals

- Auth, deployment, multi-user, mobile layout.
- Drawing arbitrary polygons.
- Redis or any message broker.
- A trace built from Temporal history (see design).
