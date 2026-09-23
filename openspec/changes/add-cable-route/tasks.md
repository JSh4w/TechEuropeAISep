## 1. Setup

- [x] 1.1 Create a server API key restricted to the Routes API and set `GOOGLE_ROUTES_API_KEY` (user, Cloud Console)
- [x] 1.2 Add `google_routes_api_key` to `config.py` and `GOOGLE_ROUTES_API_KEY=` to `.env.example`; add an autouse test fixture that unsets it so tests stay offline

## 2. Backend

- [x] 2.1 `src/bessible/api/google_routes.py`: wire models for Compute Routes (request, response) and an encoded-polyline decoder; unit-test the decoder against a known polyline
- [x] 2.2 `models.py`: `CableRoute` and the `substation_position` / `route` fields on `CapacityOutput`
- [x] 2.3 `stages/capacity.py`: set `substation_position` in `propose`, `_propose_grid_level` and `_propose_live`
- [x] 2.4 `src/bessible/cable_route.py`: `with_cable_route(position, out)` calls the Routes API (5 s timeout) and falls back to a straight line; adds the route artifact; test road, no-key and error cases with `httpx.MockTransport`
- [x] 2.5 Call `with_cable_route` in `stages.capacity.propose_capacity` and `api.capacity.check_capacity`
- [x] 2.6 `stages/financial.py` prices the cable on the route distance and names it in the cost artifact; `suitability/verdict.py` allows the route distance; test the financial change

- [x] 2.7 Start the road route at the title edge nearest the substation (planning.data title lookup, only with a Routes key); test the exit point and the no-title case

## 3. Web

- [x] 3.1 `types.ts`: `CableRoute`, `substation_position`, `route` on `CapacityOutput`
- [x] 3.2 `RunView` passes the route and the substation position to `SiteMap`
- [x] 3.3 `SiteMap`: road route solid, straight line dashed; real substation position first, name match and estimated marker as fallbacks; dashed straight line while dragging
- [x] 3.4 Legend: "Cable route by road (x km)" / "Cable run, straight line (x km)"; power lines entry names them; popups say "Distance (straight line)"

## 4. Verify

- [x] 4.1 `uv run pytest`, `ruff`, `mypy`; `npm run build` and `npm run lint` in `web/`
- [x] 4.2 Pin drop in the browser draws a road route; with the key unset it draws a dashed straight line
