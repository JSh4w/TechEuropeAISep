## Why

A listing link resolves to one point and one title. Land is often sold as several lots over several titles: a 200-acre farm "as a whole or in two lots" gets one postcode and one small title on the map, so everything after it is measured against the wrong land. On a real farm listing we tried, the page text was 18,000 characters, the listing itself started at about character 10,000 (cookie banners and menus before it), and the per-lot what3words sat past the 15,000-character cut, so the model never saw them. The same page carried the facts we needed, clean and free, in its embedded app-state JSON (position, acreage, description, lot notes, the sale plan image), which `html_to_text` throws away with every `<script>` block.

## What Changes

A tiered pipeline that uses the cheapest evidence first and spends model tokens only where the cheaper tiers fall short:

1. **Structured data (0 tokens).** Read JSON-LD, embedded app state (`__NEXT_DATA__` and equivalents) and map meta tags before scripts are stripped. Per-portal readers for Savills, Rightmove, Zoopla, Knight Frank and OnTheMarket, each a small module tested against a recorded fixture; a generic JSON-LD reader as the fallback. Output: anchor point(s), total area, address, the listing's own description, lot notes, image URLs, and a polygon when the portal has one.
2. **One small model call.** Only the listing's own description and notes (not the whole page), capped, with structured output: lots `[{name, acres, what3words, postcode, address}]`, total acres, tenure. Skipped when step 1 already gives the lots, or gives a point and the description shows a single property.
3. **Titles by acreage (0 tokens).** Around each lot's anchor, start with the INSPIRE title containing it and add adjacent titles until the area matches the stated acreage within a tolerance. Each lot is its own group, scored by area match. what3words addresses are turned into coordinates with the what3words API when a key is set; without it, the page's own point anchors the lot it falls in.
4. **Human check.** The existing confirmation step shows the chosen titles per lot; the user adds or removes titles by clicking them on the map. The confirmed set is the site for the rest of the run.
5. **Agentic step only on low confidence.** When a lot's area match is poor, find the sale plan among the gallery images cheaply (captions, file names, image statistics, then at most one low-resolution classification call), then make one vision call comparing that plan with the candidate titles drawn on a map. Cached per image URL.

Also:

- Token budget: a typical listing costs about 2k tokens or none; each model step has a stated cap. Every model call records its model in its `Artifact`.
- Single-property links keep working as today; this generalises `resolve_from_link`, and reuses the fetch cache.
- Privacy: live fetches (pages, postcodes, what3words) are cached in a gitignored directory; the committed fixture folders hold only curated demo pages, added on purpose.

## Capabilities

### New Capabilities

- `listing-lots-and-titles`: reading a listing's structured data and lots, matching each lot to a group of titles by acreage, the human edit of that set, the gated plan-image check, the token budget, and keeping tried listings out of git.

### Modified Capabilities

None as a spec delta. `link-location-extraction` (still a change, not yet in `openspec/specs/`) keeps its behaviour for single-property pages; this change states the new behaviour in its own capability.

## Non-goals

- Browser automation or JavaScript rendering: a page whose data only appears after scripts run falls back to text, as today.
- Legal title numbers or ownership: INSPIRE polygons are freehold index polygons, not title registers; a title number costs a Land Registry search.
- Reading plan images to draw new boundaries. The vision call only chooses among existing INSPIRE polygons.
- Portals beyond the five named, and title matching outside England (planning.data's `title-boundary` dataset covers England only). Elsewhere the run keeps today's single point.

## Impact

- **Code**: `src/bessible/location/fetch.py` (keep structured blocks before stripping; split cache), new `src/bessible/listing/` (portal readers, lots extraction, title grouping, plan check), `src/bessible/api/what3words.py` (wire models), `src/bessible/location/extract.py` (`resolve_from_link` uses the tiers), `src/bessible/stages/title.py` (real title groups instead of the placeholder square), `src/bessible/models.py` (`Lot`, `TitleGroup`, `TitleOutput.groups`, `SiteDecision.title_ids`), `src/bessible/workflow.py` (confirmed set), `src/bessible/location/collate.py` (accept a site polygon), `src/bessible/geocode.py` (cache split), `.gitignore`; web `types.ts`, `SiteMap.tsx`, the confirmation view, and the stub `/inspire` endpoint.
- **External**: what3words API (`WHAT3WORDS_API_KEY`, optional). Its free allowance for convert-to-coordinates must be checked before relying on it. planning.data `title-boundary` searches by polygon instead of by point.
- **Tokens**: step 2 about 2k tokens per listing that needs it; step 5 at most about 6k, only on low confidence.
- **Builds on**: the Google Maps site map (`migrate-map-to-google-maps`, merged); the click-to-toggle title layer is added there.
- **Owner**: TBD.
