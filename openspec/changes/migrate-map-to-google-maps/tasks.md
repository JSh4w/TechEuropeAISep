## 1. Google Cloud setup

- [x] 1.1 Enable the Maps JavaScript API on the `GOOGLE_MAPS_API_KEY` project and restrict the key to that SDK + `localhost` + the deployed domain (HTTP referrers); verify by confirming the restriction is saved in Cloud Console
- [x] 1.2 Create a Map ID (required for `AdvancedMarkerElement`; `DEMO_MAP_ID` is the dev fallback) and set it as `GOOGLE_MAPS_MAP_ID`; verify it shows as "Active" in Cloud Console > Maps > Map IDs

## 2. Env wiring

- [x] 2.1 Add `GOOGLE_MAPS_API_KEY` and `GOOGLE_MAPS_MAP_ID` to `.env.example` with a one-line comment on where to get them, noting the key is separate from the Gemini `GOOGLE_API_KEY`; verify by diffing against `FIREBASE_API_KEY`'s existing entry style
- [x] 2.2 In `web/src/app/layout.tsx`, add `googleMaps: { apiKey, mapId }` to the runtime config written to `window.__CONFIG__`, read from `GOOGLE_MAPS_API_KEY` / `GOOGLE_MAPS_MAP_ID`; verify `window.__CONFIG__.googleMaps.apiKey` is populated in dev
- [x] 2.3 Add `GOOGLE_MAPS_API_KEY` / `GOOGLE_MAPS_MAP_ID` to the `web` service's `environment` in `docker-compose.yml` (runtime only, no build arg); verify `docker compose config` shows them

## 3. Dependencies

- [x] 3.1 In `web/`, run `npm install @googlemaps/js-api-loader` and `npm install -D @types/google.maps`; verify `package.json` lists both
- [x] 3.2 Run `npm uninstall maplibre-gl` in `web/` and remove the MapLibre CSS import from `globals.css`; verify neither `package.json` nor `web/src` mentions `maplibre`

## 4. Map init, basemap toggle and missing-key notice

- [x] 4.1 Replace the MapLibre `Map` init in `SiteMap.tsx` with a Google `Map` constructed via the loader, passing `mapId` (fallback `DEMO_MAP_ID`); verify the map renders in `npm run dev` at the existing default center and scale (Google zoom 15.5 = MapLibre 14.5)
- [x] 4.2 Replace `handleToggleMapMode`'s `setStyle` calls with `map.setMapTypeId('roadmap' | 'satellite')`; verify clicking the toggle switches basemaps with no console errors and no flash of missing overlays
- [x] 4.3 Replace the `initialCenter` effect's `easeTo` with `panTo` + `setZoom(15.5)` (Google zoom = MapLibre zoom + 1 for the same scale); verify entering a new postcode moves the map
- [x] 4.4 With no key in `window.__CONFIG__`, skip the loader and show a "Map unavailable: set `GOOGLE_MAPS_API_KEY`" panel; set `window.gm_authFailure` to show the same panel with "Google rejected the Maps key"; verify with the key unset that the panel shows and the rest of the page works
- [x] 4.5 Turn off Google's map-type, Street View, fullscreen, rotate and camera controls; keep zoom at `RIGHT_TOP`; `gestureHandling: 'greedy'`; move the legend bar up so Google's logo and terms stay visible; verify nothing overlaps the logo or the toggle

## 5. Site marker and clamp

- [x] 5.1 Reimplement the draggable site pin as an `AdvancedMarkerElement` (`gmpDraggable`) reusing the existing HTML template, sized smaller than today's pin; verify it renders at `currentPosition`, is noticeably smaller, and the marker's anchor point still lines up with `currentPosition`
- [x] 5.2 Add `footprintHalfDiagonalKm(capacityMw, durationHours = 4)` to `web/src/lib/footprint.ts` (reuses `generateFootprintPolygon`'s side-length math); add `capacityMw` to `latestRef`; change the `dragend` handler to clamp against `Math.max(0, maxDistanceKm - footprintHalfDiagonalKm(capacityMw))`; verify a large-capacity selection clamps the pin closer to `initialCenter` than a small one, and the square's farthest corner never crosses the 2 km boundary
- [x] 5.3 Add `clampTo(pos)` to `useSiteRun` (sets `currentPosition` only: no capacity re-check, no capacity reset) and an `onPositionClamped` prop on `SiteMap`, wired in `RunView`; add a `useEffect` keyed on `[currentPosition, capacityMw, initialCenter, maxDistanceKm]` that re-runs the clamp and calls `onPositionClamped` if the pin moved; verify raising capacity near the limit pulls the pin in and leaves the slider value unchanged

## 6. Footprint and radius overlays

- [x] 6.1 Replace the footprint GeoJSON source/layers with a `google.maps.Rectangle` (bounds from `generateFootprintPolygon`'s corners) styled as outline only (no solid fill); verify the outlined square renders centered on the pin and resizes when `capacityMw` changes
- [x] 6.2 Generate an SVG diagonal-stripe `<pattern>` data URI (stripe color/weight matching the outline, translucent gaps) and render it as a `google.maps.GroundOverlay` over the same `LatLngBounds` as 6.1; verify the hatch is visible at multiple zoom levels and moves/resizes with the square
- [x] 6.3 Replace the radius line layer with a single `clickable: false` `google.maps.Polygon` that has an outer ~2° box ring and an inner ring reusing the existing 64-point circle math (wound opposite direction) as a hole; verify the 2 km boundary still renders at the right radius and the area inside stays undulled
- [x] 6.4 Style that polygon's fill (e.g. semi-transparent dark) so the area between the two rings reads as dulled, with no fill/stroke change inside the hole; verify visually that panning within the normal working zoom level never shows the outer ring's edge

## 7. Substation markers and cable ray

- [x] 7.1 Reimplement substation markers as `AdvancedMarkerElement`s with an `InfoWindow` built from the existing popup HTML; verify clicking a marker shows the same fields (route distance, voltage, headroom, marginal note)
- [x] 7.2 Reimplement the cable-ray line to the primary substation as a `google.maps.Polyline`, removed when there are no estimated substations or live `siteData` is shown; verify it draws from the pin to the first substation's coordinates and disappears when the list empties

## 8. Live site-data layer (title, grid lines, projects, real substations)

- [x] 8.1 Reimplement the title boundary as two `google.maps.Polygon`s (white unfilled halo, weight 6, below an orange filled outline, weight 3), both with `zIndex` above other overlays; "zoom to title" calls `fitBounds(bounds, 120)` and caps zoom at 19 (= MapLibre 18) with a one-shot `idle` listener; verify it renders above the footprint and the zoom stops at 19 on a small title
- [x] 8.2 Reimplement grid lines as a `google.maps.Data` layer fed by `addGeoJson`, styled by the `crosses` property; verify lines render and re-render on `siteData` updates without leaking old features
- [x] 8.3 Reimplement project and real-substation markers (from `LocationData`) as `AdvancedMarkerElement`s with `InfoWindow`s using the existing HTML templates; verify emoji icons and popups match current behavior

## 9. INSPIRE parcel overlay

- [x] 9.1 Reimplement the INSPIRE overlay as a `google.maps.Data` layer fed by `addGeoJson`, cleared when `inspireGeoJson` becomes `null`; verify it renders when present and shows nothing (no error) when it's `null`

## 10. Legend, cleanup and verification

- [x] 10.1 Update the legend: hatched "Reserved Compound (X MW)" swatch, solid (not dashed) cable and line swatches; verify it matches the drawn shapes
- [x] 10.2 Remove now-unused MapLibre imports, `StyleSpecification` constants, `GeoJSONSource` types, and the unused `areasGeoJson` prop; verify `npm run build` and `npm run lint` in `web/` succeed with no MapLibre references left
- [ ] 10.3 Manually walk every scenario in `openspec/changes/add-web-ui/specs/site-map/spec.md` and this change's `specs/site-map/spec.md` against the running app (substation ranking display, footprint move-not-resize, INSPIRE absent-safe, slider/toggle unaffected, pin re-check, confirm, title boundary from a listing link, missing-key notice) and confirm each still passes
