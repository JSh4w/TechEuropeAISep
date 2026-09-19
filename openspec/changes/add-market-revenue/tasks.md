## 1. F1 revenue-streams

- [ ] 1.1 Team decision, 20 min: name the source for each of the three streams (public only is fine) and fill the de-rating table in `data/assumptions/market.json` with source and date; verify the file has no empty value
- [ ] 1.2 Write `market/sources.py` (`RevenueSource`, Capacity Market source, fixture loader with `cached` flag); verify that a source forced to fail returns the fixture flagged cached with its date
- [ ] 1.3 Commit fixtures under `data/fixtures/market/` for all three streams; verify each loads into `StreamValue`
- [ ] 1.4 Write `market/stack.py` (per-duration stack, de-rating, totals); verify by printing the stack: totals equal the sum of streams and shorter durations earn less Capacity Market revenue
- [ ] 1.5 Replace `stages/market.py` with the real stage (one artifact per stream, `by_duration` set, `revenue_gbp_per_mw_year` = 4 h total); verify a Temporal run prints per-stream figures with sources

## 2. F2 long-duration-support (needs F1 stack)

- [ ] 2.1 Team decision, 20 min: write the qualifying rules for cap-and-floor and Ultra-LDES into `market.json` with source and date; verify that removing one rule makes the stage fail naming it
- [ ] 2.2 Write `market/support.py` `qualifying` and add support streams only to qualifying rows; verify by printing a qualifying 8 h row and a non-qualifying 2 h row (stream absent, not zero)
- [ ] 2.3 Add scheme labels to the support artifacts; verify each support artifact in a demo run names its scheme
