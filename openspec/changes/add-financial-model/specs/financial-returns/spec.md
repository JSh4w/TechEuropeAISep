## Purpose

Computes NPV and IRR for 2-hour, 4-hour and 8-hour batteries in plain code, so the duration comparison rests on arithmetic and not on model output.

## ADDED Requirements

### Requirement: Returns are computed in code
The system SHALL compute NPV and IRR for each of the 2-hour, 4-hour and 8-hour cases from revenue, cost, curtailment, interest and fees. No language model SHALL produce a financial figure.

#### Scenario: Three cases
- **WHEN** the stage completes
- **THEN** it returns exactly the durations 2, 4 and 8, each with capital cost, NPV and IRR

#### Scenario: Repeatable
- **WHEN** the stage runs twice with the same inputs
- **THEN** the figures are identical

### Requirement: Undefined IRR is reported as such
The system SHALL set IRR to unset when the cash flows never turn positive, and SHALL NOT report a number.

#### Scenario: Loss-making case
- **WHEN** total cash flows are negative in every year
- **THEN** IRR is unset and the artifact says the case does not pay back

### Requirement: Budget is checked when given
When the request has a budget, the system SHALL flag each case whose capital cost exceeds it.

#### Scenario: Over budget
- **WHEN** the budget is £5m and the 8-hour capital cost is £8m
- **THEN** the 8-hour case is flagged over budget and the other cases are judged on their own cost

### Requirement: Financing terms are documented
The system SHALL read the interest rate and arrangement fees from the assumptions file and state them in the artifact for each case.

#### Scenario: Terms shown
- **WHEN** a case is produced
- **THEN** its artifact names the interest rate and fees used
