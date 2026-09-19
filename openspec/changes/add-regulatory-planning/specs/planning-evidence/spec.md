## Purpose

Shows what has happened to nearby battery projects in planning, and summarises it in words that cite only real records.

## ADDED Requirements

### Requirement: Nearby battery projects are listed
The system SHALL list battery storage projects within 5 km of the confirmed position from the REPD snapshot, each with its name, capacity in MW, planning status and status date. It SHALL cite the dataset and snapshot date.

#### Scenario: Projects nearby
- **WHEN** 3 battery projects lie within 5 km
- **THEN** all 3 are listed with status and date

#### Scenario: None nearby
- **WHEN** no battery project lies within 5 km
- **THEN** the output says none were found

### Requirement: Summary cites records only
The system SHALL produce a short summary using Gemini with structured output. Every statement in the summary SHALL cite one or more listed project records or fixed policy items. A summary with an uncited statement SHALL be rejected and the listed records SHALL be shown alone.

#### Scenario: Cited summary
- **WHEN** the summary says "2 of 3 nearby projects are consented"
- **THEN** it cites those records

#### Scenario: Uncited statement
- **WHEN** the model returns a statement with no citation
- **THEN** the summary is rejected and the record list is shown without it

### Requirement: Fixed policy set, not retrieval
The system SHALL provide the model with a small fixed set of policy items with sources, and SHALL NOT retrieve documents at run time.

#### Scenario: Policy items
- **WHEN** the summary agent runs
- **THEN** its context contains only the fixed policy items and the listed records

### Requirement: Model is recorded
Each artifact from the summary SHALL record the model that produced it.

#### Scenario: Model name
- **WHEN** a summary artifact is created
- **THEN** its model field names the Gemini model used
