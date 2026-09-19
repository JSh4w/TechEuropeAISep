## Context

The skeleton's workflow, `RunStatus`, `AssessmentResult`, `SiteDecision` and `ConfirmedSite` already carry what the UI needs. `add-ukpn-capacity-proposal` supplies `propose()`, `CapacityOutput.alternates` and `data/ukpn/areas.geojson`. `add-footprint-sizing` supplies `reserved_acres` and `footprint_polygon`.

## Goals / Non-Goals

**Goals:** a demo-quality browser flow over the existing workflow; four features that can be built by four people after F1.

**Non-Goals:** a second orchestration path. The API only calls the same Temporal client the CLI uses.

## Decisions

### Layout

```
src/bessible/api/
  app.py        # FastAPI app
  runs.py       # start / status / decision / result
  capacity.py   # POST /capacity/check
  events.py     # SSE endpoint
src/bessible/events.py    # emit(run_id, stage, message) helper, used by activities
web/                      # Next.js app
```

### Endpoints (F1)

| Method | Path | Body → Response |
|---|---|---|
| POST | `/runs` | `AssessmentRequest` → `{run_id}` |
| GET | `/runs/{id}/status` | → `RunStatus` |
| POST | `/runs/{id}/decision` | `SiteDecision` → 204, or 422 `{allowed_min, allowed_max}` |
| GET | `/runs/{id}/result` | → `AssessmentResult`, or 409 `{status}` |
| POST | `/capacity/check` | `{position, flexible}` → `CapacityOutput` |
| GET | `/runs/{id}/events` | → `text/event-stream` |
| GET | `/data/areas.geojson` | → the committed GeoJSON |
| GET | `/inspire?bbox=` | → GeoJSON, cached |

FastAPI models are the skeleton's Pydantic models, so the types are shared, not copied. The frontend types come from FastAPI's OpenAPI schema.

### Trace (F2)

`events.emit(run_id, stage, message)` appends one JSON line to `out/<run_id>/events.jsonl`: `{"id": n, "t": "...", "stage": "...", "msg": "..."}`. The id is the line number. Activity wrappers emit start and end; agent activities emit intermediate steps. The SSE endpoint tails the file, sends `id: n` per event, and honours `Last-Event-ID` by starting at line n+1. `emit` catches every exception and logs a warning.

**Why our own log, not Temporal history:** history gives activity start and end, but the source proposal marks intermediate agent messages as unverified. A file log gives both with one mechanism and no broker. Temporal history stays the source of truth for run state.

**Logfire:** `setup_logfire()` already exists. It is wrapped so that errors are swallowed; the user trace never reads from Logfire.

### Map (F3)

MapLibre GL in Next.js. Layers: substation points with headroom labels, `areas.geojson` outline of the serving area, INSPIRE polygons, a draggable footprint polygon. The footprint is regenerated client-side from the same formula as `footprint.py` (ported once, values checked against the Python function by hand). Slider bounds come from `CapacityOutput.firm_mw` and `ceiling_mw`, the flexible toggle, and the 5 MW floor.

Pin limit: 2 km from the postcode position (assumption; the source proposal leaves it open). Re-check at the pin calls `/capacity/check`.

### Skeleton additions (owned by Josh, done in F3 tasks)

1. `SiteDecision.flexible_connection: bool | None = None`. If set, it overrides the request's value for the `ConfirmedSite` validator and is stored in run state.
2. In `decide_site` handling, if `decision.position` differs from the capacity proposal's position, the workflow runs `propose_capacity` at the new position. If that result is not viable, the run ends `not_viable` with its message. Otherwise the new capacity replaces the old one, and the decision's capacity is revalidated against it.

### Report (F4)

The page renders `AssessmentResult`. Provenance comes from each `Artifact` (`source_url`, `claim` with dataset and date). No numbers are computed in the browser.

## Risks / Trade-offs

- [Map tiles and INSPIRE need the network at demo time] → Cache INSPIRE responses for the demo pins; for tiles, pre-warm the browser cache or use a plain outline basemap as fallback.
- [Client footprint formula drifts from Python] → One tiny formula, checked by hand against the Python function for two capacities.
- [Frontend work crowds out the working CLI] → F1 to F4 are optional; the CLI stays the demo fallback.
- [Moving the pin changes capacity after the user has planned] → The page shows the new proposal and requires a new confirm.

## Open Questions

- Basemap provider (MapLibre with OpenStreetMap tiles is assumed).
- Which 2–3 demo pins get cached INSPIRE fixtures.
