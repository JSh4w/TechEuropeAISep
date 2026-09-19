## ADDED Requirements

### Requirement: Assumptions are documented
Every cost, revenue and financing input SHALL come from one assumptions file in which each value has a unit, a low/mid/high range, a source and a date. A missing value SHALL stop the stage with an error naming it. No figure SHALL be invented at run time.

#### Scenario: Missing assumption
- **WHEN** the battery cost per MWh has no value
- **THEN** the stage fails with an error naming that assumption and is not retried

### Requirement: Returns for 2, 4 and 8 hours
For the confirmed capacity, the system SHALL compute for each of 2, 4 and 8 hours: CAPEX (battery energy, balance of plant, grid connection from the distance to the substation), yearly OPEX, yearly revenue after a curtailment haircut when capacity exceeds firm capacity, financing cost from the debt share, interest rate and arrangement fee, NPV, IRR, and simple payback in years. It SHALL give low, mid and high values from the assumption ranges. The same inputs SHALL always give the same outputs.

#### Scenario: Three cases
- **WHEN** a 10 MW site is confirmed
- **THEN** the output has exactly three cases, for 2, 4 and 8 hours, each with CAPEX, NPV, IRR and payback as low, mid and high

#### Scenario: No IRR
- **WHEN** a case never pays back within the project life
- **THEN** its IRR is reported as none and its payback as beyond the project life

### Requirement: Budget check
When the request has a budget, the system SHALL flag each case whose mid CAPEX exceeds it.

#### Scenario: Over budget
- **WHEN** the budget is £5m and the 8-hour mid CAPEX is £9m
- **THEN** the 8-hour case is flagged over budget and the others are not

### Requirement: Analyst recommends a duration without writing figures
An analyst agent SHALL recommend one duration and explain the trade-off. It SHALL obtain every figure by calling the deterministic calculations and SHALL NOT state a figure that the calculations did not return. The recommendation SHALL cite the cases it compared.

#### Scenario: Recommendation
- **WHEN** the 4-hour case has the highest mid NPV within budget
- **THEN** the analyst recommends 4 hours and its explanation quotes only computed figures

### Requirement: Figures are evidence
The system SHALL emit an artifact per case and one for the assumptions used, each naming the assumptions file and its date, and SHALL label the output a screening estimate, not investment advice.

#### Scenario: Provenance
- **WHEN** the report shows a 4-hour NPV
- **THEN** its artifact names the assumptions and their sources
