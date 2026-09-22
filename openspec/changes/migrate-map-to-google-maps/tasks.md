## 1. Google Cloud setup

- [ ] 1.1 Enable the Maps JavaScript API on the `GOOGLE_MAPS_API_KEY` project and restrict the key to that SDK + `localhost`; verify by confirming the restriction is saved in Cloud Console
- [ ] 1.2 Create a Map ID (required for `AdvancedMarkerElement`) and note its value; verify it shows as "Active" in Cloud Console > Maps > Map IDs

## 2. Env wiring

- [ ] 2.1 Add `GOOGLE_MAPS_API_KEY` and `GOOGLE_MAPS_MAP_ID` to `.env.example` with a one-line comment on where to get them; verify by diffing against `FIREBASE_API_KEY`'s existing entry style
- [ ] 2.2 In `web/next.config.ts`, mirror the Firebase pattern: read `GOOGLE_MAPS_API_KEY`/`GOOGLE_MAPS_MAP_ID` from `process.env` and expose them as `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY`/`NEXT_PUBLIC_GOOGLE_MAPS_MAP_ID`; verify by logging `process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY` in a page and confirming it's populated in dev

## 3. Dependencies

- [ ] 3.1 In `web/`, run `npm install @googlemaps/js-api-loader` and its `@types` package; verify `package.json` lists it
- [ ] 3.2 Run `npm uninstall maplibre-gl` in `web/`; verify it's gone from `package.json` and `node_modules`

## 4. Map init and basemap toggle

- [ ] 4.1 Replace the MapLibre `Map` init in `SiteMap.tsx` with a Google `Map` constructed via the loader, passing `mapId`; verify the map renders in `npm run dev` at the existing default center/zoom
- [ ] 4.2 Replace `handleToggleMapMode`'s `setStyle` calls with `map.setMapTypeId('roadmap' | 'satellite')`; verify clicking the toggle switches basemaps with no console errors and no flash of missing overlays

## 5. Site marker

- [ ] 5.1 Reimplement the draggable site pin as an `AdvancedMarkerElement` reusing the existing HTML template, sized smaller than today's pin; verify it renders at `currentPosition`, is noticeably smaller, and the marker's anchor point still lines up with `currentPosition`
- [ ] 5.2 Add `footprintHalfDiagonalKm(capacityMw, durationHours)` to `web/src/lib/footprint.ts` (reuses `generateFootprintPolygon`'s side-length math) and change the `dragend` handler's `clampPositionWithinDistance` call to clamp against `Math.max(0, maxDistanceKm - footprintHalfDiagonalKm(capacityMw))` instead of `maxDistanceKm`; verify a large-capacity selection clamps the pin closer to `initialCenter` than a small one, and the Reserved Compound square's farthest corner never crosses the 2 km boundary
- [ ] 5.3 Add a `useEffect` keyed on `capacityMw` that re-runs the same clamp against the current pin position and calls `onPositionChange` if it moved; verify increasing capacity while the pin sits near its limit pulls the pin (and square) back inside the boundary without a drag

## 6. Footprint and radius overlays

- [ ] 6.1 Replace the footprint GeoJSON source/layers with a `google.maps.Rectangle` (bounds from `generateFootprintPolygon`'s corners) styled as outline only (no solid fill); verify the outlined square renders centered on the pin and resizes when `capacityMw` changes
- [ ] 6.2 Generate an SVG diagonal-stripe `<pattern>` data URI (stripe color/weight matching the outline, translucent gaps) and render it as a `google.maps.GroundOverlay` over the same `LatLngBounds` as 6.1; verify the hatch is visible at multiple zoom levels and moves/resizes with the square
- [ ] 6.3 Replace the radius line layer with a single `google.maps.Polygon` that has an outer ~2° box ring and an inner ring reusing the existing 64-point circle math (wound opposite direction) as a hole; verify the 2 km boundary still renders at the right radius and the area inside stays undulled
- [ ] 6.4 Style that polygon's fill (e.g. semi-transparent dark) so the area between the two rings reads as dulled, with no fill/stroke change inside the hole; verify visually that panning within the normal working zoom level never shows the outer ring's edge

## 7. Substation markers and cable ray

- [ ] 7.1 Reimplement substation markers as `AdvancedMarkerElement`s with an `InfoWindow` built from the existing popup HTML; verify clicking a marker shows the same fields (route distance, voltage, headroom, marginal note)
- [ ] 7.2 Reimplement the cable-ray line to the primary substation as a `google.maps.Polyline`; verify it draws from the pin to the first substation's coordinates

## 8. Live site-data layer (title, grid lines, projects, real substations)

- [ ] 8.1 Reimplement the title-boundary overlay as a `google.maps.Polygon` with explicit `zIndex` above other overlays (replacing the fill/halo/outline `moveLayer` stack); verify it renders above the footprint and the "zoom to title" button still calls `fitBounds` correctly
- [ ] 8.2 Reimplement grid lines as a `google.maps.Data` layer fed by `addGeoJson`, styled by the `crosses_site` property; verify lines render and re-render on `siteData` updates without leaking old `Data` layers
- [ ] 8.3 Reimplement project and real-substation markers (from `LocationData`) as `AdvancedMarkerElement`s with `InfoWindow`s using the existing HTML templates; verify emoji icons and popups match current behavior

## 9. INSPIRE parcel overlay

- [ ] 9.1 Reimplement the INSPIRE overlay as a `google.maps.Data` layer fed by `addGeoJson`; verify it renders when `inspireGeoJson` is present and shows nothing (no error) when it's `null`

## 10. Cleanup and verification

- [ ] 10.1 Remove now-unused MapLibre imports, `StyleSpecification` constants, and `GeoJSONSource` types from `SiteMap.tsx`; verify `npm run build` in `web/` succeeds with no MapLibre references left
- [ ] 10.2 Manually walk every scenario in `openspec/changes/add-web-ui/specs/site-map/spec.md` against the running app (substation ranking display, footprint move-not-resize, INSPIRE absent-safe, slider/toggle unaffected, pin re-check, confirm) and confirm each still passes
