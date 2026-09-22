## Context

`web/src/components/SiteMap.tsx` is a single client component built imperatively around MapLibre GL: refs hold the `Map` and marker instances, a chain of `useEffect`s add/replace GeoJSON sources and paint layers, and a manual style-swap (`STREETS_MAP_STYLE` / `SATELLITE_MAP_STYLE`, two hand-written Esri raster `StyleSpecification` objects) drives the streets/satellite toggle. Overlays today: draggable site marker (custom HTML `div`, clamped to 2 km via `clampPositionWithinDistance`), a footprint polygon (`generateFootprintPolygon` in `web/src/lib/footprint.ts`, fill+outline), a 2 km radius circle (hand-computed as a 64-point polygon), substation markers with `Popup` HTML, a cable-ray line to the primary substation, a title-boundary polygon (fill+halo+outline, kept above everything via `moveLayer`), grid-line/project/substation markers from live `LocationData`, and an INSPIRE parcel overlay (arbitrary-count `FeatureCollection`, fill+outline). See proposal.md for why this is being swapped.

## Goals / Non-Goals

**Goals:**
- 1:1 behavioral parity with every overlay listed above, using the Google Maps JavaScript API as the renderer.
- Keep the component's imperative, ref-based shape so the diff is a renderer swap, not a rewrite of the surrounding page/state logic.

**Non-Goals:**
- Pixel-identical styling. Google's `Polygon`/`Polyline` don't support dashed strokes natively; accept solid strokes rather than building a dash workaround.
- The current map's `pitch: 15` tilt. Tilt on Google's vector basemap needs a vector-enabled Map ID and specific zoom/rendering conditions; drop it for v1 (consistent with the proposal's non-goal on 3D Maps).

## Decisions

**Loader: `@googlemaps/js-api-loader`, not `@vis.gl/react-google-maps`.** The React wrapper is declarative (map state driven through JSX/props) and would mean rearchitecting the ref/`useEffect` structure this component already uses. The plain loader just resolves a promise once `google.maps` is on `window`; the rest of the component keeps its current shape.

**Basemap toggle: `map.setMapTypeId('roadmap' | 'satellite')`, replacing the two hand-written `StyleSpecification` objects and the `style.load` re-add dance.** Google ships both basemaps built in — no custom tile source, no re-adding overlays after a style swap (overlays are independent objects, not part of a "style," so they survive the toggle for free). Net simplification, not just a swap.

**Markers → `google.maps.marker.AdvancedMarkerElement`**, not the legacy `google.maps.Marker`. `AdvancedMarkerElement` takes a `content` DOM node, so the existing custom-HTML marker templates (site pin, substation badges, project emoji pins) carry over largely unchanged. Requires the `marker` library in the loader config and a **Map ID** (see Risks).

**Popups → `google.maps.InfoWindow`**, opened via `infoWindow.open({ anchor: marker, map })`. The existing HTML template strings for substation/project/substation-headroom popups carry over unchanged.

**Overlay geometry — split by whether the feature count is fixed or data-driven:**
- Fixed single-feature overlays (footprint, radius boundary + dulled exterior, cable-ray, title boundary) → discrete typed objects: `google.maps.Polygon` for footprint, the radius mask, and title, `google.maps.Polyline` for the cable ray. Discrete objects also give real `zIndex` control (`polygon.setOptions({ zIndex })`), which replaces the current `moveLayer` calls used to keep the title boundary on top — simpler and more direct.
- Data-driven, arbitrary-count `FeatureCollection`s (INSPIRE parcels, live grid lines from `LocationData`) → `google.maps.Data` layers via `addGeoJson`, one `Data` instance per overlay so they can be styled and cleared independently (mirrors today's one-source-per-overlay pattern).

**Reserved Compound square: `google.maps.Rectangle` for the outline + a `google.maps.GroundOverlay` for the diagonal-stripe fill, not a `Polygon`.** Neither `Polygon` nor `Rectangle` support a pattern fill — `fillColor` is solid-color only. `generateFootprintPolygon`'s square is always axis-aligned (a plain min/max lat/lng box, never rotated), so it maps directly onto `Rectangle`'s `LatLngBounds` — simpler than `Polygon` for a plain box, and it gives native `strokeColor`/`strokeWeight` for the outline. The diagonal hatch itself is built as an SVG `<pattern>` (diagonal lines at the outline's color/weight, low-opacity gaps for the "translucent between stripes" look), encoded as a data URI, and shown as a `GroundOverlay` image stretched over the same `LatLngBounds`. SVG `patternUnits="userSpaceOnUse"` tiles regardless of the image's rendered size, so one small SVG produces a consistent hatch at any zoom — no canvas/redraw wiring needed, both objects reproject automatically like any native Maps overlay.

**Pin clamp now accounts for the Reserved Compound square's size, not just its center.** Today `clampPositionWithinDistance` clamps the pin to `maxDistanceKm` from `initialCenter`; since the square is centered on the pin, its farthest corner sits `halfDiagonal` beyond the pin itself, so a center-only clamp lets corners cross the 2 km line near the edge. Fix: add `footprintHalfDiagonalKm(capacityMw, durationHours)` to `footprint.ts` (reuses the existing side-length math from `generateFootprintPolygon`) and clamp the pin to `Math.max(0, maxDistanceKm - halfDiagonalKm)` instead of `maxDistanceKm`. Because this also needs to hold after a capacity change (not just at drag time), add a `useEffect` keyed on `capacityMw` that re-runs the same clamp against the current pin position and calls `onPositionChange` if it moved — same function, one more call site, no new logic.

**Radius boundary + dulled exterior: one `google.maps.Polygon` with a hole, not a plain `google.maps.Circle`.** The requirement is two things at once: a visible boundary at 2 km (already existed) and a dimmed exterior beyond it (new). A `Circle` can only fill or stroke its own interior — it has no way to represent "everywhere outside a circle," and Google's map `styles` option (a global tile-rendering stylesheet) can't be scoped to a shape either, so a "dull everywhere, bright circle on top" approach doesn't work: styling renders the base tiles dull permanently, and an overlay drawn on top can only add paint, never restore the original tile colors underneath. A single `Polygon` with two rings — an outer ring far beyond any reasonable zoom (~2° box) and an inner ring matching the 2 km circle, wound in the opposite direction — fills only the area between the rings (even-odd rule), leaving the interior untouched, and strokes both rings, so the inner ring's stroke is the same boundary line a standalone `Circle` would have drawn. This does **not** drop the manual point-generation math the way a plain `Circle` would have: `Polygon` needs explicit `LatLng` coordinates for the inner ring, so today's 64-point circle computation in `SiteMap.tsx` is kept and repurposed to build that ring, rather than deleted. This overlay is purely visual — it does not enforce the pin's movement limit; that stays entirely in `clampPositionWithinDistance` (`web/src/lib/footprint.ts`), unrelated to which Maps object draws the circle.

## Risks / Trade-offs

[Risk] `AdvancedMarkerElement` requires a Map ID configured in Google Cloud Console (a plain API key alone isn't enough) → Mitigation: create a free Map ID as part of setup (tasks.md), pass it as `mapId` when constructing the map, document it next to `GOOGLE_MAPS_API_KEY` in `.env.example`.

[Risk] No native dashed stroke on `Polygon`/`Polyline` (used today for the footprint outline, radius circle, cable ray, and INSPIRE outline) → Mitigation: ship solid strokes; this is cosmetic only and doesn't affect any `site-map` requirement.

[Risk] Dropping `pitch: 15` is a small visual regression from the current tilted view → Mitigation: none needed, explicitly a non-goal; revisit only if the flat map looks worse in practice.

[Risk] The dulled-exterior mask's outer ring is a fixed ~2° box, not viewport-relative → panning far enough from the site would show unmasked map past its edge → Mitigation: size it generously (~2° is far beyond any reasonable zoom-out for a 2 km site check); not a functional requirement, so no dynamic resize needed.

[Risk] At a large enough capacity, `halfDiagonalKm` could exceed `maxDistanceKm`, making the effective clamp distance negative → Mitigation: floor it at `Math.max(0, ...)`, which pins the marker to `initialCenter` in that extreme case rather than erroring.

## Migration Plan

1. Cloud Console: enable Maps JavaScript API on `GOOGLE_MAPS_API_KEY`, create a Map ID, restrict the key to this SDK + `localhost` and the deployed domain.
2. Wire `GOOGLE_MAPS_API_KEY` → `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY` in `web/next.config.ts` (mirrors the existing Firebase pattern) and add both the key and Map ID to `.env.example`.
3. `npm install @googlemaps/js-api-loader` (+ types), `npm uninstall maplibre-gl` in `web/`.
4. Rewrite `SiteMap.tsx` overlay-by-overlay in the order above (map init → marker → footprint → radius boundary + dulled exterior → substation markers/popups → cable ray → title/grid `Data` layer → INSPIRE `Data` layer → basemap toggle), so each overlay can be checked against its current behavior before moving to the next.
5. Manual QA against the `site-map` spec scenarios: drag clamps at 2 km, footprint moves without resizing, area outside 2 km reads visually dulled while the pin's reachable area stays clear, INSPIRE overlay is absent-safe, substation popups show the right fields, basemap toggle works, title boundary stays visually on top.

**Rollback:** the change is scoped to one component, one lib file's consumption (not its GeoJSON generation, which is unchanged), `package.json`, and `next.config.ts` — a single revert commit restores MapLibre with no data-model or persisted-state cleanup needed.
