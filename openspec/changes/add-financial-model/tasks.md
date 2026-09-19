## 1. F1 cost-model (start here)

- [ ] 1.1 Team decision, 30 min: agree and write the null values in `data/assumptions/finance.json` (battery £/MWh, balance of plant, OPEX, crossing uplift, oversubscription %, discount and interest rates, fees, project life), each with source and date; verify no `null` remains for a value the code needs
- [ ] 1.2 Write `finance/assumptions.py` (load, validate, `MissingAssumption`); verify that loading a copy of the file with one needed value set to null raises with that key's name
- [ ] 1.3 Write `finance/cost.py` for capex, opex and connection cost with crossing uplift; verify by printing costs for 1 km (£500k–£700k), 3 km (£1.5m–£2.1m), a crossing case, and that capex rises with duration
- [ ] 1.4 Add the proposed fee line with the 50% / 25% thresholds; verify by printing 60% (active, labelled proposed), 20% (inactive) and 40% (inactive)

## 2. F2 curtailment-estimate (independent of F1)

- [ ] 2.1 Write `data/assumptions/demand_profile.json` (source named) and `finance/curtailment.py` `load_duration_curve`; verify the printed curve's max and min equal the substation's max and min demand
- [ ] 2.2 Write `curtailment_pct` with the overlap-only method; verify by printing 0% at firm capacity, a positive value between firm and ceiling, and a value below the raw constrained-hours share

## 3. F3 financial-returns (needs F1 and one revenue figure)

- [ ] 3.1 Write `finance/returns.py` NPV, IRR (unset when never positive), financing terms; verify by printing a case with known cash flows and a loss-making case (IRR unset), and that two runs give the same numbers
- [ ] 3.2 Add the budget check and the optional `DurationCase` fields; verify a printed run with a £5m budget flags only the over-budget case
- [ ] 3.3 Replace `stages/financial.py` with the real stage (three cases, artifacts stating rate, fees, curtailment assumption); verify a Temporal run prints the duration table with computed numbers

## 4. F4 narration-guard (independent of F1–F3)

- [ ] 4.1 Write `guard.check_narration` with number extraction and 5% tolerance; verify from a Python shell that a matching number passes, an invented number is listed, and a rounded number passes
- [ ] 4.2 Write `guarded()` with 2 retries and the templated fallback; verify with a stub narrator that fails twice then passes, and one that always fails (fallback text used, fallback artifact recorded)
- [ ] 4.3 Apply the guard in `stages/synthesis.py` for findings that state figures; verify a run with a stub narrator that invents a figure never writes it to `report.md`
