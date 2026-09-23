## Why

The hackathon is over; this is portfolio polish. MapLibre GL (the current renderer in `web/src/components/SiteMap.tsx`) is functionally solid but visually generic. Google Maps' basemap and interaction feel is instantly familiar to reviewers, looks more finished, and Google Deepmind/Google sponsored the hackathon this project was built for — using their Maps SDK strengthens the portfolio story. This is a rendering-layer swap only; no user-facing map behavior changes.

## What Changes

- Replace `maplibre-gl` with the Google Maps JavaScript API as the map renderer in `web/src/components/SiteMap.tsx`.
- Reimplement, on the new renderer, each interaction the current map already has: draggable site marker (clamped to 2 km of the postcode position), the generated footprint polygon (drag-to-move, not draw), the title boundary from `/site-data` with "zoom to title", INSPIRE land-registry polygon overlay, substation markers with popups, site-data markers with popups.
- Pass `GOOGLE_MAPS_API_KEY` and `GOOGLE_MAPS_MAP_ID` from the root `.env` to the browser at **runtime**, through the same `window.__CONFIG__` object `web/src/app/layout.tsx` already writes for Firebase — not as `NEXT_PUBLIC_*` build-time values, which would bake the key into the prebuilt GHCR image. Add both to `.env.example` and to the `web` service in `docker-compose.yml`.
- `GOOGLE_MAPS_API_KEY` is a separate browser key. It is not `GOOGLE_API_KEY` (the Gemini key), which must never reach the browser.
- Restrict the new API key to the Maps JavaScript API only — no Places, Geocoding, Routes, Street View, or 3D SKUs — and to `localhost` plus the deployed domain. Postcode → coordinates keeps using `api.postcodes.io` (free, already working); it is not being replaced by Google Geocoding.
- New: dim/mask the map area outside the 2 km screening radius, so the area the pin can't be dragged into reads visually as out of scope, not just implied by a boundary line.
- Shrink the site pin marker.
- Restyle the footprint square to match the "Reserved Compound" size already shown in `SiteControls.tsx`'s stat tile: outline plus a diagonal-stripe hatch in the same color/weight as the outline, translucent between stripes (replacing today's flat fill). The map legend shows the same hatch and the "Reserved Compound" label.
- New: the Reserved Compound square's full extent — not just the pin's center — SHALL stay within the 2 km screening radius, at drag time, after a capacity change, and after the screening centre moves. Tightens the existing pin clamp.
- New: when the Maps key is missing or Google rejects it, the map card shows a "Map unavailable" notice instead of a blank or broken map. The rest of the page keeps working.
- **BREAKING** (dev-only): anyone running the web app locally now needs a `GOOGLE_MAPS_API_KEY` set to see the map (without it they get the notice above).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `site-map` (`openspec/changes/add-web-ui/specs/site-map/spec.md`, not yet synced to main specs): adds four requirements — the map visually dims the area outside the 2 km screening radius; the Reserved Compound square's full extent (not just the pin's center) is kept within that same radius; the title boundary of the assessed site is drawn (this existed in code but had no requirement, and it is how a submitted listing link shows its property boundary); and a missing or rejected Maps key shows a notice. Everything else in that spec — footprint drag, INSPIRE overlay, substation ranking, slider, toggle, pin re-check, confirm — is unaffected; only the rendering library underneath changes.

## Non-goals

- No quota or budget capping for the new API key (handled separately later).
- No Places Autocomplete, Geocoding API, Routes/Directions, Street View, or 3D Maps — out of scope, not needed by current functionality.
- No change to how postcodes or listing links resolve to coordinates, and no change to where the title boundary comes from (HM Land Registry, through `/site-data`). Google only draws it.
- No behavior change to any map interaction — this is a like-for-like renderer swap, apart from the new requirements above.

## Impact

- **Code**: `web/src/components/SiteMap.tsx` (full rewrite of the rendering internals), `web/src/lib/footprint.ts` (new `footprintHalfDiagonalKm`; GeoJSON generation unchanged), `web/src/lib/useSiteRun.ts` + `web/src/components/workspace/RunView.tsx` (a clamp-only position setter), `web/src/app/layout.tsx` (runtime config), `web/src/app/globals.css` (drop the MapLibre CSS import), `.env.example`, `docker-compose.yml`, root `.env`.
- **Dependencies**: remove `maplibre-gl`; add `@googlemaps/js-api-loader` and `@types/google.maps`.
- **External**: new Google Cloud project / API key requirement for anyone running the web app.
- **Owner**: Einar.
