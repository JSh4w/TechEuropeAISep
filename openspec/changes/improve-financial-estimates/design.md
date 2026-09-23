## Context

See proposal.md for the problem. Current state that shapes the approach:

- `stages/financial.py` calls `finance.cost.cost`, `finance.curtailment.curtailment_pct` and `finance.returns.returns` once per duration, with mid values only. `DurationCase.low` / `high` exist but are always `None`.
- `AssumptionSet.number(key)` reads `value`. Ranged entries in `finance.json` also carry `low` / `mid` / `high`, and for the battery cost `value` (250k) differs from `mid` (140k).
- `suitability/finance.py` already computes low/mid/high with a pessimistic/optimistic combination, but nothing on the report path calls it.
- The location layer already parses DNO demand: `Substation.max_demand_summer_mva` / `max_demand_winter_mva`, and the UKPN, NPg and SPEN wire models have `demandmaximum` / `demandminimum`. `CapacityOutput` does not carry them to the financial stage.
- Market revenue goes through `RevenueSource.fetch(duration_h) -> StreamValue`, with `FallbackSource(live, fixture)` already written but no live source wired.
- The report UI now reads `result.financial` (done in this branch, before this change).
- Every number below is justified, or flagged as unverified, in `research.md`.

## Goals / Non-Goals

**Goals:**
- Every figure that differs between two sites traces to a named site input in an artifact.
- The existing stage and activity signatures stay the same; all new model fields are optional.

**Non-Goals:**
- Merging `suitability/finance.py` into `finance/`. We copy its bound logic; deleting the duplicate is a later clean-up.
- Half-hourly dispatch against curtailment. Curtailment stays the daily overlap estimate.

## Decisions

### D1. One accessor for ranged assumptions
Add `AssumptionSet.at(key, bound: Bound) -> float`, where `Bound = Literal["low", "mid", "high"]`. `number(key)` returns `mid` when the entry has one. `AssumptionSet.load` fails if an entry has both `value` and `mid` and they differ, and the error names the key. Remove `value` from ranged entries in `finance.json`.
*Alternative:* change `value` to 140k only. Rejected, because the two fields can drift apart again.

### D2. Bounds by running the model three times
`stages/financial.py` runs cost → curtailment → returns once per bound. Each function gets a `bound: Bound = "mid"` keyword and reads every ranged input with `a.at(key, bound)`. For the "low" bound, costs and rates use `high` and revenue uses `low` (the same combination as in `suitability/finance.py`). A table in `finance/bounds.py` holds this, `PESSIMISTIC: dict[str, Bound]`, so the direction per key is in one place.
*Alternative:* sensitivity per input. Rejected, because the report shows one range, and a sensitivity per input is more work than the demo needs.

### D3. Carry substation demand through `CapacityOutput`
New optional fields, set by both the snapshot and the live capacity paths:
```python
substation_max_demand_mw: float | None = None
substation_min_demand_mw: float | None = None
demand_source: str | None = None       # dataset name, used in the artifact
licence_area: str | None = None        # e.g. "UKPN LPN", used for the EET demand zone
```
MVA figures are converted with the existing `POWER_FACTOR`. The live path takes the larger of summer/winter max. The minimum comes from `demandminimum` where published. Add `min_demand_mva` to `location.models.Substation` and map it in `location/transform.py` for UKPN, NPg and SPEN.
`finance/curtailment.py` gains a pure function:
```python
class DemandBounds(NamedTuple):
    max_mw: float
    min_mw: float
    assumed: Literal["none", "min", "both"]
    source: str

def demand_bounds(cap: CapacityOutput, a: AssumptionSet) -> DemandBounds
```
When the max is present but the min is missing, min = max × `substation_min_demand_ratio` (new assumption). When both are missing, the function uses the UKPN primary median (15.8 MW max, ratio 0.29; research.md §6) instead of the old 40/10 MW. Artifact confidence: 0.85 / 0.7 / 0.5 for none / min / both assumed.

### D4. Embedded export credit as one national figure
Research (research.md §3) shows the Embedded Export Tariff averages £3.05/kW (about £3k/MW/yr, roughly 4% of revenue). It is paid only on export during the three Triad peak periods. That is too small to justify a zonal table, so the model uses one ranged assumption in `finance.json`:
```json
"eet_gbp_per_kw": {"low": 0, "mid": 3.05, "high": <highest zone>, "unit": "GBP/kW/year",
                   "source": "NESO Final TNUoS Tariffs 2026/27, Table 13", "date": "2026-01-31"}
```
The low bound is £0 because a battery can miss the Triad periods. Pure function in `finance/network.py`:
```python
class NetworkCharge(BaseModel):
    gbp_per_mw_year: float   # negative = credit
    kind: Literal["eet", "not_modelled"]
    tariff_year: str

def network_charge(mw: float, a: AssumptionSet, bound: Bound) -> NetworkCharge
```
Sites at or above 100 MW return `kind="not_modelled"` with 0 and a flagged artifact, because generation TNUoS applies to them instead. It enters the cash flow as an annual line, indexed like opex.
*Alternative:* a zonal EET table plus a generation-TNUoS branch by GSP. Rejected, because it is a large table for about 1% of NPV, and NESO publishes the zonal table as an image.

### D5. Development cost and land lease in `cost()`
Add `development_gbp` (fixed per project, ranged, placeholder) to CAPEX. This fixed cost is what makes cost per MW fall as MW rises. An earlier draft used a balance-of-plant scale exponent, but no source supports one (research.md §1). Add an annual `land_lease_gbp_per_acre_year` (ranged £10k/£25k/£40k) to opex, times the reserved acres from the footprint stage. `CostBreakdown` gains `development_gbp` and `land_lease_gbp_per_year`.

### D6. Elexon arbitrage source with a monthly cache
- `src/bessible/api/elexon.py`: wire model `MarketIndexRow(startTime, settlementPeriod, price, volume, dataProvider)` and `async fetch_market_index(start: date, end: date) -> list[MarketIndexRow]` against the BMRS `datasets/MID` endpoint. It requests 7-day windows (check the API's max range at implementation) and uses the `APXMIDP` provider.
- `src/bessible/market/arbitrage.py`: pure `arbitrage_gbp_per_mw_year(days: list[list[float]], duration_h: int, rte: float) -> float`. Each day holds 48 half-hour prices. Per day, it discharges in the `2*duration_h` highest periods and charges in the `2*duration_h` lowest periods, with one cycle a day. The model does not require the charge periods to come before the discharge periods; this is a known optimism, covered by the capture factor below. Revenue = Σ sold × price − Σ bought × price, where bought = sold / rte. Days with a negative result count as zero, because the battery would not cycle on those days.
- `ElexonArbitrageSource(RevenueSource)` caches the daily price arrays in `out/cache/elexon_mid_<yyyy-mm>.json`. It re-fetches only the current month, so a warm run makes ≤2 requests. It is wrapped in `FallbackSource` with the wholesale fixture. `default_sources()` uses it when `settings.live_market` is true (new setting, default true). Round-trip efficiency is ranged 85/87.5/90% (NREL ATB: 85%). The capture factor is ranged 60/80/90% and marked placeholder (research.md §2).
*Alternative:* the day-ahead N2EX auction. Rejected, because MID is free, keyless and already on Elexon.

### D7. Capacity Market as a sourced assumption
EMR publishes auction results as PDFs and spreadsheets, and has no API. Update `capacity_market.json` to £27.10/kW/yr (T-4 for 2029/30, cleared 10 March 2026). Update `capacity_market_derating` in `market.json` to 2 h = 0.2094. The 4 h and 8 h factors stay placeholder until someone copies them from NESO's capacity report table; they are not extrapolated, because the factors level off for long durations. When checked, set `status: "agreed"`. The stream claim says "published auction result".

### D8. Year-by-year cash flow
`finance/returns.py` replaces the flat annual net with:
```python
class Lifecycle(BaseModel):
    fade_pct_per_year: float
    augmentation_year: int
    augmentation_gbp_per_mwh: float
    restored_capacity_pct: float
    ancillary_decline_pct_per_year: float
    ancillary_decline_years: int
    inflation_pct: float
    tax_rate_pct: float
    capital_allowance_first_year_pct: float
    allowance_eligible_share: float
    decommissioning_gbp_per_mw: float

class YearFlow(BaseModel):
    year: int
    capacity_factor: float
    revenue_gbp: float
    opex_gbp: float
    network_gbp: float
    debt_service_gbp: float
    tax_gbp: float
    capex_gbp: float
    equity_flow_gbp: float

def cash_flows(cost, streams: dict[str, float], curtail_pct, network: NetworkCharge,
               f: Financing, life: Lifecycle) -> list[YearFlow]
```
Revenue per stream is multiplied by `capacity_factor` (fade, then reset at augmentation). Both `balancing_ancillary` and `wholesale` decline, each at its own documented rate (research.md §2). Revenue, opex and network charges are indexed by inflation. The discount rate is nominal. Tax losses carry forward. `npv` / `irr` take `[y.equity_flow_gbp for y in flows]`. Payback years come from the cumulative equity flow (copy `_payback_years` from `suitability/finance.py`). Starting values go in `finance.json` with sources: fade 2%/yr (LFP warranty curves), one augmentation event in year 8 (range 5–11), CT 25%, full expensing at 100% first year on the plant share, CPI 2%.

### D9. Report ranges
`CaseBound` already has capex, NPV, IRR and payback. `web/src/lib/types.ts` adds `low?` / `high?` to `FinancialCase`. `ReportView` shows "£x.xxM (£low–£high)" for NPV and IRR in the matrix and hero cards. `reportExport.ts` adds two range columns.

## Risks / Trade-offs

- [Elexon slow or down during a demo] → The cache is warmed by `uv run python -m bessible.market warm`. `FallbackSource` uses the fixture after a 20 s timeout, and the artifact says "cached".
- [MID prices overstate the spread a real battery captures (perfect foresight)] → Multiply by the documented capture factor and say so in the claim.
- [Unverified inputs (balance of plant, development cost, capture factor, 4 h/8 h de-rating)] → Each ships as `status: "placeholder"`, and the artifact says so until someone checks it.
- [Three model runs triple the runtime] → The whole model is pure arithmetic, well under 50 ms per run, so this is not a problem.
- [In-flight specs not archived] → This change adds requirements to capabilities from `add-financial-model` / `add-market-revenue` / `add-web-ui`. Archive those first.

## Migration Plan

All new fields are optional, so older `result.json` files (for example `data/demo/dorking/`) still load. Regenerate the demo result after the change lands. Rollback: set `live_market=false` for fixtures and revert the finance.json values.

## Open Questions

- Discount rate and hurdle (research.md Q1) and balance-of-plant scope (Q2). These are data changes in `finance.json`, not design changes.
