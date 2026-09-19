## Context

Replaces the skeleton's `market_revenue` placeholder (`NodeInput → MarketOutput`). `MarketOutput` today has `revenue_gbp_per_mw_year` and `streams`. It runs in parallel with `grid_connection` and `site_land`, so it depends only on the confirmed site and capacity.

## Goals / Non-Goals

**Goals:** a working revenue stack for the demo without a paid feed; a clean place to plug one in later.

**Non-Goals:** price forecasting; anything that needs a paid key.

## Decisions

### Layout

```
src/bessible/market/
  sources.py     # RevenueSource protocol + public Capacity Market source + fixtures
  stack.py       # per-duration stack (F1)
  support.py     # cap-and-floor / Ultra-LDES (F2)
data/assumptions/market.json      # de-rating table, qualifying rules
data/fixtures/market/*.json       # committed fallbacks, one per stream
```

### Interfaces

```python
class StreamValue(BaseModel):
    stream: str                       # "capacity_market" | "balancing_ancillary" | "wholesale" | "cap_and_floor" | "ultra_lds"
    gbp_per_mw_year: float
    source: str
    source_url: HttpUrl
    as_of: date
    cached: bool

class RevenueSource(Protocol):
    name: str
    async def fetch(self, duration_h: int) -> StreamValue: ...

async def revenue_stack(mw: float, sources: list[RevenueSource], a: MarketAssumptions) -> dict[int, list[StreamValue]]
def qualifying(duration_h: int, mw: float, a: MarketAssumptions) -> list[str]   # support streams that apply
```

`MarketOutput` gains optional `by_duration: dict[int, list[StreamValue]]`. The existing `revenue_gbp_per_mw_year` is the 4-hour total, so `add-financial-model` works before it reads `by_duration`.

**Why a `RevenueSource` protocol:** the blocker is a data-source decision. Any source, public or paid, implements one method, so the decision does not change the stage.

### Sources for the demo

Capacity Market: a public source plus fixture. Balancing/ancillary and wholesale: fixture-backed until the team names a source. Each fixture records its origin and date, so nothing is presented as live.

## Risks / Trade-offs

- [Fixtures look like live data] → `cached: true` and the fixture date are in every artifact claim.
- [Qualifying rules are wrong] → They live in one documented file the team can edit.
- [Decision on paid feed never made] → Public-only path is complete on its own.

## Open Questions

- The rules for which durations and sizes qualify for cap-and-floor and Ultra-LDES (task 2.1 needs the team to fill them).
