## Purpose

Reports how much other demand competes for the same substation capacity, separately from the accepted queue, so the developer sees the pressure without distorting the headroom figure.

## ADDED Requirements

### Requirement: Competing demand is reported, not subtracted
The system SHALL report, for the serving substation, the MW of offers made but not accepted, budget estimates provided, and LTDS Table 6 enquiries, and a weighted total in which each category weighs less than an accepted connection offer. The system SHALL NOT subtract the weighted total from effective headroom.

#### Scenario: Reported separately
- **WHEN** a substation has 10 MW of offers not accepted and 20 MW of enquiries
- **THEN** an artifact lists each category and the weighted total, and effective headroom is unchanged

#### Scenario: No records
- **WHEN** the substation has no records in any category
- **THEN** the weighted total is zero and the artifact says no records were found

### Requirement: Pressure is banded
The system SHALL classify competition pressure as low when the weighted total is below 0.5 times effective headroom, medium when it is below 1 times, and high otherwise.

#### Scenario: High pressure
- **WHEN** the weighted total is 12 MW and effective headroom is 10 MW
- **THEN** the pressure is high

### Requirement: Queue shrinkage is caveated
The system SHALL include a context artifact stating that effective headroom subtracts the current accepted queue and may be pessimistic if speculative projects leave it.

#### Scenario: Caveat present
- **WHEN** any capacity proposal is made
- **THEN** the caveat artifact is included
