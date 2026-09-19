## Why

The skeleton's `market_revenue` returns fixed numbers, and nothing yet says where a real revenue stack comes from. The financial model needs revenue per MW for each duration, with a source for every stream.

**Owner:** TBD.

## What Changes

Two features. F1 first; F2 adds to it.

- **F1 revenue-streams:** a revenue stack per duration from named streams: Capacity Market clearing prices (public), balancing mechanism and ancillary services, and wholesale arbitrage. Each stream carries a source and date. A live source that fails falls back to a cached fixture, flagged as cached.
- **F2 long-duration-support:** cap-and-floor and Ultra-LDES streams appear only on rows that qualify. Rows that do not qualify omit them; they are not shown as zero.

## Capabilities

### New Capabilities

- `revenue-streams`: per-duration revenue stack with sources, de-rating and fixtures.
- `long-duration-support`: qualifying-row rules for cap-and-floor and Ultra-LDES.

### Modified Capabilities

None.

## Impact

- New `src/bessible/market/` package and `data/assumptions/market.json`, `data/fixtures/market/`.
- Replaces `stages/market.py`. `MarketOutput` gains an optional `by_duration` field.
- Feeds `add-financial-model` (`revenue_gbp_per_mw_year` per duration).

## Blockers

- **No revenue data source.** Capacity Market prices are public. Balancing Mechanism, ancillary and arbitrage revenues are largely commercial (Modo Energy, LCP Delta) or need historical prices. *Needs a decision:* which sources, and whether a paid feed is acceptable. Until decided, F1 ships with public sources and committed fixtures only.

## Non-goals

- A paid feed integration (needs the decision above).
- Forecasting future prices or dispatch optimisation.
- Cost and returns (`add-financial-model`).
