## Why

The skeleton's `financial_model` returns fixed numbers. Real IRR and NPV need a documented cost basis, a curtailment estimate, and a guarantee that any LLM narration repeats only the computed figures.

**Owner:** TBD.

## What Changes

Four features. F1 comes first; F2, F3 and F4 build on it or run alongside.

- **F1 cost-model:** CAPEX, OPEX, and grid connection cost from route length (33 kV underground £500,000–£700,000 per km; the 132 kV rate £1.25m–£2m per km is recorded but unused). Adds the proposed Ofgem Oversubscribed Technologies Commitment Fee as a CAPEX line at £3,000–£25,000 per MW, marked proposed. All inputs come from a documented assumptions file.
- **F2 curtailment-estimate:** synthesised load duration curve, with the haircut applied only where constrained hours overlap dispatch hours.
- **F3 financial-returns:** NPV and IRR for 2 h, 4 h and 8 h in plain code, including interest and fees, with a budget check.
- **F4 narration-guard:** checks every number in LLM-written text against typed run state.

## Capabilities

### New Capabilities

- `cost-model`: documented assumptions, CAPEX and OPEX, connection cost, proposed fee line.
- `curtailment-estimate`: load duration curve and overlap-only haircut.
- `financial-returns`: NPV, IRR and budget check for three durations.
- `narration-guard`: number validation for narrated text.

### Modified Capabilities

None.

## Impact

- New `src/bessible/finance/` and `src/bessible/guard.py`; `data/assumptions/finance.json`.
- Replaces `stages/financial.py`. `FinancialOutput` gains optional fields only.
- Uses `distance_km` and `ceiling_mw` from the capacity stage and `revenue_gbp_per_mw_year` from the market stage.

## Blockers

- **No CAPEX or OPEX baseline.** No £/MWh for the battery, no balance-of-plant or annual OPEX figure. *Needs a decision:* the team agrees and documents the values in `finance.json` (task 1.1). Nothing else in this change produces real IRR until then.

## Non-goals

- Using the 132 kV rate (no grid-level data yet).
- Dispatch optimisation or a full tax model.
- The revenue side (`add-market-revenue`).
- Measured curtailment data. The estimate is a documented assumption.
