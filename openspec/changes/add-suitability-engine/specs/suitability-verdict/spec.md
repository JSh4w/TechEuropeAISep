## ADDED Requirements

### Requirement: Verdict comes from rules, not the model
The system SHALL decide go, maybe or no-go with fixed rules over the typed results: the recommended case's mid IRR against a hurdle rate, whether it is within budget, the opposition index, and curtailment. The rules and thresholds SHALL be stated in the report. A language model SHALL NOT change the verdict.

#### Scenario: Go
- **WHEN** the recommended case clears the hurdle rate, is within budget, and the opposition index is below 0.5
- **THEN** the verdict is go

#### Scenario: Opposition drags it down
- **WHEN** the finances clear the hurdle but the opposition index is above 0.7
- **THEN** the verdict is maybe and the top concerns are named as the reason

#### Scenario: Unknown sentiment
- **WHEN** the opposition index is unknown
- **THEN** the verdict is decided on finances alone and the report says sentiment was not available

### Requirement: Findings are narrated and cited
The system SHALL produce plain-language findings covering feasibility, finances and local sentiment. Every finding SHALL cite at least one artifact id that exists in the run.

#### Scenario: Citations
- **WHEN** the report is produced
- **THEN** every finding lists artifact ids present in the run's artifact list

### Requirement: Numbers in the narrative are checked
Every number in narrated text SHALL match a computed value within 5%. When a finding contains an unmatched number, the system SHALL ask for a rewrite once, and if it still fails SHALL fall back to a template finding built from the typed values.

#### Scenario: Invented figure
- **WHEN** the narration states an IRR of 14% and the computed IRR is 9%
- **THEN** the finding is rewritten or replaced, and the report never shows 14%

### Requirement: The report is written to the run folder
The system SHALL write the report with the verdict, the rules applied, the three-duration table, the opposition index with top concerns, and the findings with their citations, to the run's folder.

#### Scenario: Report file
- **WHEN** a run completes
- **THEN** the run folder contains the report and it states the verdict and the rules that produced it
