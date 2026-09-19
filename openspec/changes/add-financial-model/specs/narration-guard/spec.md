## Purpose

Guarantees that numbers in language-model-written text match the typed figures in run state, so a report can never state a figure the system did not compute.

## ADDED Requirements

### Requirement: Narrated numbers are checked against run state
The system SHALL extract every number with a unit from narrated text and check that each matches a figure in the typed run state, allowing for rounding. The system SHALL reject narration that contains a number not present in run state.

#### Scenario: Matching number
- **WHEN** the text says "NPV of £1.2m" and run state has an NPV of £1,204,000
- **THEN** the narration passes

#### Scenario: Invented number
- **WHEN** the text says "IRR of 14%" and run state has no IRR of about 14%
- **THEN** the narration is rejected

### Requirement: Rejected narration is retried, then replaced
On rejection, the system SHALL retry the narration up to 2 times with the mismatch named. If it still fails, the system SHALL use a templated sentence built from run state.

#### Scenario: Retry succeeds
- **WHEN** the first narration is rejected and the second passes
- **THEN** the second is used

#### Scenario: Fallback
- **WHEN** all attempts are rejected
- **THEN** the templated text is used and an artifact records the fallback

### Requirement: Applies to every narrating stage
The system SHALL apply the guard to the synthesis stage and to any stage that narrates figures.

#### Scenario: Synthesis
- **WHEN** the synthesis stage writes a finding that states a figure
- **THEN** the guard has checked it
