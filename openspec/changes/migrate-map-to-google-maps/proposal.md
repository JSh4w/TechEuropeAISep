## Why

The hackathon is over; this is portfolio polish. MapLibre GL (the current renderer in `web/src/components/SiteMap.tsx`) is functionally solid but visually generic. Google Maps' basemap and interaction feel is instantly familiar to reviewers, looks more finished, and Google Deepmind/Google sponsored the hackathon this project was built for — using their Maps SDK strengthens the portfolio story. This is a rendering-layer swap only; no user-facing map behavior changes.

## What Changes

- Replace `maplibre-gl` with the Google Maps JavaScript API as the map renderer in `web/src/components/SiteMap.tsx`.
- Reimplement, on the new renderer, each interaction the current map already has: draggable site marker (clamped to 2 km of the postcode position), the generated footprint polygon (drag-to-move, not draw), INSPIRE land-registry polygon overlay, substation markers with popups, site-data markers with popups.
- Wire `GOOGLE_MAPS_API_KEY` from the root `.env` into `web/next.config.ts` as `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY`, mirroring the existing `FIREBASE_API_KEY` → `NEXT_PUBLIC_FIREBASE_API_KEY` pattern. Add `GOOGLE_MAPS_API_KEY=` to `.env.example`.
- Restrict the new API key to the Maps JavaScript API only — no Places, Geocoding, Routes, Street View, or 3D SKUs. Postcode → coordinates keeps using `api.postcodes.io` (free, already working); it is not being replaced by Google Geocoding.
- New: dim/mask the map area outside the 2 km screening radius, so the area the pin can't be dragged into reads visually as out of scope, not just implied by a boundary line.
- Shrink the site pin marker.
- Restyle the footprint square to match the "Reserved Compound" size already shown in `SiteControls.tsx`'s stat tile: outline plus a diagonal-stripe hatch in the same color/weight as the outline, translucent between stripes (replacing today's flat fill).
- New: the Reserved Compound square's full extent — not just the pin's center — SHALL stay within the 2 km screening radius, at drag time and if the user changes capacity afterward. Tightens the existing pin clamp.
- **BREAKING** (dev-only): anyone running the web app locally now needs a `GOOGLE_MAPS_API_KEY` set, or the map fails to load.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `site-map` (`openspec/changes/add-web-ui/specs/site-map/spec.md`, not yet synced to main specs): adds two requirements — the map visually dims the area outside the 2 km screening radius, and the Reserved Compound square's full extent (not just the pin's center) is kept within that same radius. Everything else in that spec — footprint drag, INSPIRE overlay, substation ranking, slider, toggle, pin re-check, confirm — is unaffected; only the rendering library underneath changes, plus these two new requirements.

## Non-goals

- No quota or budget capping for the new API key (handled separately later).
- No Places Autocomplete, Geocoding API, Routes/Directions, Street View, or 3D Maps — out of scope, not needed by current functionality.
- No change to how postcodes resolve to coordinates.
- No behavior change to any map interaction — this is a like-for-like renderer swap.

## Impact

- **Code**: `web/src/components/SiteMap.tsx` (full rewrite of the rendering internals), `web/src/lib/footprint.ts` (GeoJSON generation stays, but consumption changes from MapLibre's `GeoJSONSource` to the Google Maps `Data` layer or `Polygon`/`Circle` objects), `web/next.config.ts` (env wiring), `.env.example`, root `.env`.
- **Dependencies**: remove `maplibre-gl`; add a Google Maps JS loader (e.g. `@googlemaps/js-api-loader`).
- **External**: new Google Cloud project / API key requirement for anyone running the web app.
- **Owner**: Einar.
