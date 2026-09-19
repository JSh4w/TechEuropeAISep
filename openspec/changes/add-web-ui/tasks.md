## 1. F1 web-api (start here)

- [x] 1.1 Add `fastapi` and `uvicorn` with `uv add`; write `api/app.py` and `api/runs.py` with `POST /runs`, `GET /runs/{id}/status`, `GET /runs/{id}/result`; verify with `curl` that a start returns a run id and status shows `awaiting_confirmation` for a demo postcode
- [x] 1.2 Add `POST /runs/{id}/decision` with the 422 range error and 404; verify with `curl` that an out-of-range capacity returns the allowed range and a valid one continues the run
- [x] 1.3 Add `POST /capacity/check`, `/data/areas.geojson` and the Temporal-down 503; verify with `curl` that the check returns in under 1 s and that stopping Temporal gives the `temporal server start-dev` message

## 2. F2 live-trace

- [x] 2.1 Write `events.py` `emit` (append-only JSONL, never raises) and call it from the activity wrappers on stage start and end; verify a demo run creates `out/<run_id>/events.jsonl` with increasing ids
- [x] 2.2 Add `GET /runs/{id}/events` (SSE, tails the file, closes after the final event); verify with `curl -N` that events appear live during a run
- [x] 2.3 Support `Last-Event-ID`; verify with `curl -N -H "Last-Event-ID: 3"` that the first event has id 4
- [x] 2.4 Wrap Logfire setup so errors are swallowed and add an `emit` call for agent progress in one agent stage; verify a run completes with a bad `LOGFIRE_TOKEN` and the trace still streams

## 3. F3 site-map (needs F1; also uses `add-footprint-sizing`)

- [ ] 3.1 Scaffold `web/` with Next.js and MapLibre and generate types from the FastAPI OpenAPI schema; verify `npm run dev` shows an empty map
- [ ] 3.2 Start a run from a postcode form and plot the serving substation, alternates, headroom labels and the marginal flag; verify by starting a run and seeing the points on the map
- [ ] 3.3 Add the draggable generated footprint and the size slider (bounds, MW and acres, curtailment cue above firm); verify by dragging and by sliding at both toggle states
- [ ] 3.4 Add the flexible toggle (default off) and the not-viable "try flexible" prompt; verify a below-floor postcode shows the prompt and restarting with the toggle on works
- [ ] 3.5 Add the INSPIRE proxy `GET /inspire?bbox=` with cached demo fixtures and the overlay; verify a demo pin shows polygons and an area with none shows no error
- [ ] 3.6 Add the 2 km pin limit and re-check via `/capacity/check`, with the new-substation message; verify by dragging the pin across an area boundary
- [ ] 3.7 Skeleton additions: `SiteDecision.flexible_connection` and workflow re-proposal on a moved position; verify a confirm at a moved position ends `not_viable` for a bad spot and continues for a good one
- [ ] 3.8 Send the confirm decision (position, capacity, footprint, toggle) from the page; verify the run continues and the status page updates

## 4. F4 web-report (needs F1)

- [ ] 4.1 Build the report page from `AssessmentResult` with the five sections; verify a completed run shows all five
- [ ] 4.2 Show source, date and artifact link beside each figure, and the screening notice above the fold; verify by clicking one figure's link and reading the notice
- [ ] 4.3 Add the live trace panel using the SSE stream (needs F2); verify the trace scrolls during a run and resumes after reloading the page

## 5. Wrap-up

- [ ] 5.1 Run the full flow in the browser for the three demo postcodes; verify viable, below-floor-with-flexible, and out-of-area each end as expected
