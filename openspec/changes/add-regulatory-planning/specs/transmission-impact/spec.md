## Purpose

Tells the developer that the project needs a Transmission Impact Assessment, and what that means for who is involved and how long it takes.

## ADDED Requirements

### Requirement: The TIA threshold is stated
The system SHALL state the serving substation's Transmission Impact Assessment threshold (1 MW or 5 MW), with the dataset and snapshot date as the source.

#### Scenario: Threshold shown
- **WHEN** the serving substation has a 5 MW threshold
- **THEN** the output states 5 MW and cites the dataset

### Requirement: Triggering is stated
When the confirmed capacity is at or above the threshold, the system SHALL state that a Transmission Impact Assessment is triggered and that NESO involvement and Gate 2 timescales apply.

#### Scenario: Triggered at the floor
- **WHEN** the threshold is 5 MW and the confirmed capacity is 5 MW
- **THEN** the output states the assessment is triggered

#### Scenario: Threshold 1 MW
- **WHEN** the threshold is 1 MW and the confirmed capacity is 8 MW
- **THEN** the output states the assessment is triggered

### Requirement: Threshold data missing
When the threshold is not known, the system SHALL say so and SHALL NOT assume it is triggered or not.

#### Scenario: Unknown threshold
- **WHEN** the snapshot has no threshold for the substation
- **THEN** the output says the threshold is unknown
