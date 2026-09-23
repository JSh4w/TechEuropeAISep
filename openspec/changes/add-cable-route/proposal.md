## Why

The map draws the connection cable as a straight line from the pin to the serving substation, and the finance model prices the cable on that straight-line distance (`finance/cost.py`). A real distribution cable is laid mostly under local roads and around obstacles, so it is longer than the straight line. The straight line under-prices the connection and looks more certain than it is. At the Dorking demo point, the road route is 0.85 km where the straight line is 0.57 km.

## What Changes

- After the capacity check, compute a road route from the site to the serving substation with the Google Routes API (Compute Routes, Essentials tier: drive, no traffic, avoid motorways). Keep a straight line as the fallback when no key is set or the call fails, and say which one was used.
- `CapacityOutput` gains the serving substation's position and the cable route (distance, path, method). `distance_km` keeps its meaning: straight-line distance, used for the marginal flag and ranking.
- The financial model prices the cable on the route distance when there is one.
- An artifact records the route: distance, method, and the straight-line distance next to it.
- The map draws the road route as a solid line, or a dashed straight line when there is no road route, and the legend says which. Substation popups say "Distance" (straight line), not "Route Distance". The power-lines legend entry says what the lines are.
- New setting `GOOGLE_ROUTES_API_KEY`: a server-side key restricted to the Routes API, separate from the browser Maps key.

## Capabilities

### New Capabilities

- `cable-route`: road route from the site to the serving substation, its fallback, and its use in the cost model and on the map.

### Modified Capabilities

None as a spec delta. The map's cable line already exists in code (see `migrate-map-to-google-maps`); this change states its behaviour in the new capability.

## Non-goals

- The DNO's actual cable design. A road route is still an estimate: it knows nothing of wayleaves, existing ducts or the operator's design.
- Traffic-aware routing, waypoints, tolls: they move the request to a paid tier and mean nothing for a cable.
- Storing routes long-term: Google's terms restrict caching route results.

## Impact

- **Code**: new `src/bessible/api/google_routes.py` (wire models), `src/bessible/cable_route.py` (call + fallback), `src/bessible/models.py`, `src/bessible/stages/capacity.py`, `src/bessible/api/capacity.py`, `src/bessible/stages/financial.py`, `src/bessible/suitability/verdict.py`, `src/bessible/config.py`; web `types.ts`, `RunView.tsx`, `SiteMap.tsx`.
- **External**: Routes API, one call per capacity check (pin drop or run). Free up to 10,000 calls a month on the Essentials tier.
- **Config**: `GOOGLE_ROUTES_API_KEY` in `.env.example`.
- **Owner**: Einar.
