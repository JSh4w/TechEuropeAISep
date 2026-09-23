## 1. Report shows real figures (done before this change)

- [x] 1.1 Report and markdown export read `result.financial` with no placeholder cases; "No payback" for unset IRR; discount rate and project life come from `FinancialOutput`. Verified: `npx tsc --noEmit` clean, `uv run pytest` passes.

## 2. One agreed figure per assumption (D1)

- [ ] 2.1 Add `Bound` and `AssumptionSet.at(key, bound)`, make `number()` prefer `mid`, and fail `load` when `value` and `mid` differ. Verify: new tests in `tests/test_financial.py` for `at`, `number` and the mismatch error naming the key.
- [ ] 2.2 Remove `value` from ranged entries in `data/assumptions/finance.json`. Verify: `uv run pytest tests/test_financial.py` passes and the 5 MW, 0.3 km, 4 h probe gives a positive IRR.
- [ ] 2.3 Replace the source names that research.md §7 could not find with the real sources from research.md, or set `status: "placeholder"`. Verify: `grep` finds none of the §7 names in `data/assumptions/`.

## 3. Substation demand drives curtailment (D3)

- [ ] 3.1 Add `min_demand_mva` to `location.models.Substation` and map `demandminimum` in `location/transform.py` for UKPN, NPg and SPEN. Verify: `uv run python -m bessible.location <lat> <lon>` shows the field for a UKPN site.
- [ ] 3.2 Add `substation_max_demand_mw`, `substation_min_demand_mw`, `demand_source` and `licence_area` to `CapacityOutput`, and set them in the snapshot and live paths of `stages/capacity.py`. Verify: a test in `tests/test_stages.py` with a UKPN fixture row asserts the MW values.
- [ ] 3.3 Add `demand_bounds()`, `substation_min_demand_ratio` (0.29) and the UKPN-median default bounds (15.8 MW max), and use them in `stages/financial.py` with the "assumed" wording and confidence levels. Verify: tests cover none / min / both assumed, and two capacity outputs with different demand give different curtailment.

## 4. Low and high bounds end to end (D2, D9)

- [ ] 4.1 Add `finance/bounds.py` with the pessimistic direction per key, and a `bound` keyword on `cost`, `curtailment_pct` and `returns`. Verify: a test asserts low NPV ≤ mid ≤ high for 20 MW at 2/4/8 h.
- [ ] 4.2 Run the three bounds in `stages/financial.py` and fill `DurationCase.low` / `high` with capex, NPV, IRR and payback. Verify: `uv run pytest tests/test_stages.py` and a `FinancialOutput` with bounds validates.
- [ ] 4.3 Show "mid (low–high)" for NPV and IRR in `ReportView.tsx` hero cards and matrix, and add range columns in `reportExport.ts`. Mirror `CaseBound` in `web/src/lib/types.ts`. Verify: `npx tsc --noEmit` clean, and the demo report renders ranges.

## 5. Cost realism (D4, D5)

- [ ] 5.1 Add `development_gbp` to `cost()` and `land_lease_gbp_per_acre_year` times reserved acres to opex, as new ranged assumptions. Verify: a test shows capex per MW at 40 MW is below that at 5 MW, and a 3-acre site at £25k/acre adds £75k/yr.
- [ ] 5.2 Add the ranged `eet_gbp_per_kw` assumption (0 / 3.05 / highest zone from NESO Table 13) and `finance/network.py` with `network_charge()`. Verify: tests for a 20 MW site (£61k credit at mid, £0 at low) and a 120 MW site (not modelled, flagged).
- [ ] 5.3 Pass the network charge into the returns and name the tariff year in the cost artifact. Verify: the artifact claim in a stage test contains "2026/27".

## 6. Year-by-year cash flow (D8)

- [ ] 6.1 Add `Lifecycle` assumptions to `finance.json` (fade, augmentation, decline, CPI, tax, allowances, decommissioning), each with source and date, plus `Lifecycle.from_assumptions`. Verify: loading fails and names the key when one is missing.
- [ ] 6.2 Rewrite `cash_flows` to return `list[YearFlow]` with fade, augmentation, revenue decline (balancing and wholesale) and inflation, and change `npv` / `irr` to use the equity flows. Verify: tests for "year 5 revenue < year 1 revenue" and "year 12 capacity restored".
- [ ] 6.3 Add corporation tax with capital allowances and loss carry-forward, plus payback years. Verify: a test shows zero tax in early loss years and lower tax later.
- [ ] 6.4 Pass the market stream split (not only the total) into `returns` from `stages/financial.py`. Verify: `uv run pytest` passes in full.

## 7. Live wholesale arbitrage (D6)

- [ ] 7.1 Add `src/bessible/api/elexon.py` with the `MarketIndexRow` wire model and `fetch_market_index()` in 7-day windows (the API rejects longer ranges), keeping only `APXMIDP` rows (N2EX rows are zero). Verify: a live call for one week returns about 336 APXMIDP rows.
- [ ] 7.2 Add the pure `market/arbitrage.py` with round-trip efficiency (85% mid), the capture factor (80% mid, placeholder) and the zero floor. Verify: tests with a synthetic day give the hand-calculated value and 8 h ≥ 4 h ≥ 2 h.
- [ ] 7.3 Add `ElexonArbitrageSource` with the monthly cache in `out/cache/`, wrap it in `FallbackSource`, and add `settings.live_market`. Verify: a test with a failing fetch returns the fixture flagged cached.
- [ ] 7.4 Add `uv run python -m bessible.market warm` to fill the cache for 12 months. Verify: a second run makes at most 2 requests (log line).

## 8. Capacity Market from the latest auction (D7)

- [ ] 8.1 Set `capacity_market.json` to £27.10/kW/yr (T-4 2029/30) and the 2 h de-rating factor to 0.2094. Name the auction in `source`, and change the claim text to "published auction result". Verify: the 2 h Capacity Market stream is about £5,675/MW/yr, and `tests/test_market.py` passes.
- [ ] 8.2 Copy the 4 h and 8 h de-rating factors from NESO's capacity report table and set them to `agreed`. Verify: the market artifact no longer says placeholder.

## 9. End-to-end check

- [ ] 9.1 Run two live assessments at different sites (different DNO, size and distance). Verify: capex, NPV, IRR, curtailment and the artifact inputs differ between the two reports, and every financial artifact names its site inputs.
- [ ] 9.2 Regenerate `data/demo/dorking/result.json`. Verify: `uv run pytest tests/test_demo.py` passes and the demo report shows ranges.
