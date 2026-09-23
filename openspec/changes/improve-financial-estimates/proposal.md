## Why

The financial model gives nearly the same answer for every site. Revenue per MW comes from three placeholder fixtures, curtailment uses one fixed 40/10 MW substation for all sites, battery cost reads £250k/MWh (so 4 h and 8 h never pay back), and every one of the 25 years has the same cash flow. Estimates must differ by site and trace to their inputs.

**Owner:** Einar.

## What Changes

- **Site facts drive cost and curtailment.** One agreed battery cost figure. Curtailment scales between the serving substation's own maximum and minimum demand from DNO data (UKPN, NGED, SSEN, SPEN, NPg), with the fixed figures only as a flagged fallback. Add the Embedded Export Tariff credit for sites under 100 MW, a fixed development cost (which makes cost per MW fall with size) and a land lease cost.
- **Live market revenue.** Wholesale arbitrage from 12 months of Elexon market index prices, for 2 h, 4 h and 8 h, net of round-trip losses. Capacity Market price (£27.10/kW/yr, T-4 2029/30) and de-rating factors from the latest auction. Fixtures stay as the flagged fallback.
- **Year-by-year cash flow.** Capacity fade with an augmentation capex, a revenue decline curve, inflation indexing, corporation tax with capital allowances, and decommissioning cost.
- **Ranges, not single figures.** Each duration case gets low and high bounds; the report shows them.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

These capabilities are defined in the in-flight changes `add-financial-model`, `add-market-revenue` and `add-web-ui` (not yet archived to `openspec/specs/`). This change adds requirements to them.

- `cost-model`: single battery cost figure, embedded export credit, development cost, land lease.
- `curtailment-estimate`: per-substation demand bounds with a flagged fallback.
- `financial-returns`: year-by-year cash flow, tax, degradation, low/high bounds.
- `revenue-streams`: live wholesale arbitrage and Capacity Market sources.
- `web-report`: show low/mid/high ranges per duration case.

## Impact

- `src/bessible/finance/` (cost, curtailment, returns), `src/bessible/market/sources.py`, `src/bessible/stages/financial.py`, `src/bessible/stages/capacity.py`.
- `data/assumptions/finance.json`, `market.json`. `research.md` justifies every number.
- `CapacityOutput` and `CaseBound` gain optional fields only; `web/src/lib/types.ts` mirrors them.
- New Elexon BMRS calls (free, no key) in the market activity only.

## Non-goals

- Northern Ireland sites. NI is in the all-island SEM market, outside GB wholesale, balancing and Capacity Market data.

- Dispatch optimisation or a trading simulation.
- Paid revenue feeds (Modo, Aurora).
- Monte Carlo analysis.
- A full UK tax model (only corporation tax and main capital allowances).
