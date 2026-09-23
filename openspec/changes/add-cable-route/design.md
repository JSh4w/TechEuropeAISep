## Context

Capacity is proposed in `stages/capacity.py` (`propose` from the UKPN snapshot, `propose_live` from live DNO data, `verify_live` re-checking the snapshot) and returned by the Temporal activity and by `POST /capacity/check` (pin drops). `CapacityOutput.distance_km` is the straight-line (haversine) distance to the serving substation; `stages/financial.py` passes it to `finance/cost.py`, which prices the cable per km. The serving substation's coordinates are known inside the capacity stage (snapshot row or live substation) but are not returned, so the map has had to guess where to draw the cable.

## Goals / Non-Goals

**Goals:** a road-following route and its distance on the capacity output; the cost model uses it; the map draws it; a clear fallback when there is no route.

**Non-Goals:** DNO cable design, traffic, caching routes beyond a request.

## Decisions

**Routes API, Compute Routes Essentials.** `POST https://routes.googleapis.com/directions/v2:computeRoutes` with `travelMode: DRIVE`, `routingPreference: TRAFFIC_UNAWARE`, `routeModifiers.avoidHighways: true`, field mask `routes.distanceMeters,routes.polyline.encodedPolyline`. None of these are Pro or Enterprise triggers, so each call bills as Essentials (10,000 free a month). DRIVE on local roads is the closest proxy for "under the highway", where distribution cables are usually laid; motorways are avoided because cables do not follow them.

**Called from the backend, after the capacity proposal.** One helper, `with_cable_route(position, out)`, runs in both `stages.capacity.propose_capacity` (the activity) and `api.capacity.check_capacity` (pin drops). The proposal functions stay pure; the helper does the I/O. Backend, not browser, so the cost model and the report get the same distance the map shows.

**Server key, separate from the browser key.** `GOOGLE_ROUTES_API_KEY` (`settings.google_routes_api_key`). The browser Maps key is public and should be restricted to the Maps JavaScript API and our domains; a server key is restricted to the Routes API (and, in production, the server's IP).

**Fallback: straight line, labelled.** No key, a non-200 response, no route, or a timeout (5 s) gives `CableRoute(method="straight_line", distance_km=<haversine>, path=[site, substation])`. Never fails the capacity check.

**The road route starts at the title edge nearest the substation.** Starting at the pin let Google snap it to the nearest road, which for a pin on the far side of a plot meant going the long way round. Now the helper looks up the title the pin sits in (one planning.data `title-boundary` request, the same one `collate` makes), takes the point on its edge nearest the substation, and routes from there. The path is `[pin, exit point, *road, substation]`, and the distance adds the straight on-site leg (pin to exit point: the cable runs on the owner's land). No title, or the substation on the title: route from the pin as before. The lookup only runs when a Routes key is set, since a straight line does not need it.

**Path ends at the pin and the substation.** Google snaps origin and destination to the nearest road, so the returned polyline can start and end a little away from them. The path is `[site, *polyline, substation]`, so the drawn line meets both markers. The distance is Google's `distanceMeters` plus the two straight off-road legs (site to the first road point, last road point to the substation).

**Model.** `CableRoute(distance_km: float, path: list[Position], method: Literal["road", "straight_line"])`. `CapacityOutput` gains `substation_position: Position | None` and `route: CableRoute | None`. `distance_km` is unchanged (straight line) because the ranking, the marginal flag (> 1 km) and the capacity artifacts are defined on it.

**Cost model uses the route distance.** `stages/financial.py` takes `capacity.route.distance_km` when a route exists, else `distance_km` as today. The cost artifact says which distance was used. `suitability/verdict.py` adds the route distance to the numbers the verdict may quote.

**Artifact.** One capacity artifact per route: "Cable route to {substation}: {x} km by road (Google Routes API, local roads, motorways avoided); straight line {y} km", or "…: {y} km straight line (no road route: {reason})". `model_used`: `google-routes-api` or `straight-line`.

**Map.** The map already draws a cable line from the pin to the serving substation. It now uses `route.path` (road: solid line) and `substation_position` (real coordinates, no name matching) when the capacity output has them. With no route (demo recordings, loading) it draws a dashed straight line to the substation marker, as before. While the pin is dragged the line becomes a dashed straight line from the pin; the road route returns after the drop and re-check. The legend reads "Cable route by road (x km)" or "Cable run, straight line (x km)".

## Risks / Trade-offs

[Risk] A road route is still not the DNO's route → Mitigation: the artifact and legend say "by road"; the non-goal is stated in the proposal.

[Risk] Routes API cost → Mitigation: Essentials only; one call per capacity check; free to 10,000 a month.

[Risk] A pin in a large field snaps to a road some distance away → Mitigation: the path joins the pin to the snapped start with a short straight leg, so the gap is visible rather than hidden.

[Risk] Extra latency on pin drops → Mitigation: 5 s timeout; typical call is a few hundred ms.

## Migration Plan

1. Create a server API key in Cloud Console restricted to the Routes API; set `GOOGLE_ROUTES_API_KEY`.
2. Deploy. Without the key, everything works as before with straight-line routes.
