## Context

Replaces the skeleton's `financial_model` placeholder (`FinancialInput → FinancialOutput`). Inputs it uses: `capacity.distance_km`, `capacity.firm_mw`, `capacity.ceiling_mw`, `site.capacity_mw`, `market.revenue_gbp_per_mw_year`, and `site_land` constraints. Money is computed in plain code (CLAUDE.md and the source proposal agree).

## Goals / Non-Goals

**Goals:** four features that can be built by four people in parallel after the assumptions file exists.

**Non-Goals:** dispatch optimisation, tax, a real load profile dataset.

## Decisions

### Layout

```
src/bessible/finance/
  assumptions.py   # load + validate data/assumptions/finance.json
  cost.py          # F1
  curtailment.py   # F2
  returns.py       # F3
src/bessible/guard.py   # F4
data/assumptions/finance.json
data/assumptions/demand_profile.json
```

### Assumptions file

```json
{
  "battery_gbp_per_mwh":   {"value": null, "unit": "GBP/MWh", "source": "", "date": ""},
  "balance_of_plant_gbp_per_mw": {"value": null, "unit": "GBP/MW", "source": "", "date": ""},
  "opex_gbp_per_mw_year":  {"value": null, "unit": "GBP/MW/year", "source": "", "date": ""},
  "cable_33kv_gbp_per_km": {"value": [500000, 700000], "unit": "GBP/km", "source": "team brief", "date": "2026-09-19"},
  "cable_132kv_gbp_per_km":{"value": [1250000, 2000000], "unit": "GBP/km", "source": "team brief", "date": "2026-09-19", "used": false},
  "crossing_uplift_pct":   {"value": null, "unit": "%", "source": "", "date": ""},
  "otcf_gbp_per_mw":       {"value": [3000, 25000], "unit": "GBP/MW", "source": "Ofgem consultation opened 2026-09-17", "date": "2026-09-19", "status": "proposed"},
  "otcf_on_above_pct": 50, "otcf_off_below_pct": 25, "oversubscription_pct": {"value": null},
  "discount_rate": {"value": null}, "interest_rate": {"value": null}, "arrangement_fee_pct": {"value": null},
  "project_life_years": {"value": null}
}
```

Values that are `null` are the team's decision (proposal, Blockers). The loader raises `MissingAssumption("<key>")` for any null a computation needs. The known figures come from the source brief; nothing else is invented here.

### Interfaces

```python
# F1
class CostBreakdown(BaseModel):
    duration_h: Literal[2, 4, 8]
    capex_gbp: float
    opex_gbp_per_year: float
    connection_gbp: tuple[float, float]      # low, high
    otcf_gbp: tuple[float, float] | None     # None when inactive; always labelled "proposed"
def cost(duration_h: int, mw: float, distance_km: float, crossings: bool, a: Assumptions) -> CostBreakdown

# F2
def load_duration_curve(max_mw: float, min_mw: float, profile: list[float]) -> list[float]   # 8760 values
def curtailment_pct(capacity_mw: float, firm_mw: float, ceiling_mw: float, curve: list[float], duration_h: int) -> float

# F3
def returns(cost: CostBreakdown, revenue_gbp_per_mw_year: float, curtail_pct: float, mw: float, a: Assumptions) -> DurationCase
# skeleton DurationCase gains optional fields: over_budget: bool = False, curtailment_pct: float | None = None

# F4
def check_narration(text: str, state: dict[str, float]) -> list[str]        # unmatched numbers, empty = pass
async def guarded(narrate: Callable[[str | None], Awaitable[str]], state: dict[str, float], template: str) -> str
```

### Curtailment method

Constrained hours: hours where the curve is above the firm-import limit (peak side) or below the export limit (trough side). Dispatch hours: the battery discharges in the top `duration_h` hours of each day's curve and charges in the bottom `duration_h`. Curtailment percentage is the share of dispatch hours that are also constrained, scaled by `(capacity - firm) / (ceiling - firm)`. This is a documented assumption; the source proposal lists the overlap size as an open question.

### Narration guard

Numbers are extracted with a regex for `£`, `%`, `MW`, `MWh`, `km`, `months` and `years`. A match needs a relative difference under 5% against any value in `state` (`state` is flattened from the typed outputs). Simple and testable; not a semantic check.

## Risks / Trade-offs

- [Baseline values never agreed] → F1 task 1.1 is the decision gate; until then the stage returns `irr=None` and an artifact "no cost baseline agreed".
- [Guard rejects true rewordings such as "about a third"] → Text must state figures numerically; the prompt for narration says so.
- [Overlap method is crude] → Named as an assumption in every curtailment artifact.

## Open Questions

- Source of the standard demand profile (must be named in `demand_profile.json`).
- Whether oversubscription percent is a fixed assumption or fetched later.
