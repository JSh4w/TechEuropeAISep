## Purpose

Bases the export side of the capacity ceiling on published reverse power capability and transformer ratings, instead of the demand side alone.

## ADDED Requirements

### Requirement: Export ceiling comes from Table 2a
When LTDS Table 2a has records for the serving substation, the system SHALL compute an export ceiling from the reverse power capability percentage and the seasonal transformer ratings. The overall ceiling SHALL be the lower of the import ceiling and the export ceiling, and SHALL NOT be below the firm capacity.

#### Scenario: Export ceiling is lower
- **WHEN** the import ceiling is 9 MW and the export ceiling is 6 MW
- **THEN** the overall ceiling is 6 MW, or the firm capacity if that is higher

#### Scenario: No Table 2a data
- **WHEN** the serving substation has no Table 2a record
- **THEN** the ceiling uses the import side only and an artifact says the export ceiling is unavailable

### Requirement: Export ceiling is validated before use
The system SHALL apply the export ceiling only if a validation check has passed: no substation with a registered battery in the Embedded Capacity Register has an overall ceiling below that battery's registered capacity. The result of the check SHALL be stored in the snapshot manifest.

#### Scenario: Validation passes
- **WHEN** the check finds no substation below its registered battery capacity
- **THEN** the export ceiling is applied

#### Scenario: Validation fails
- **WHEN** the check finds one or more substations below their registered battery capacity
- **THEN** the export ceiling is not applied and the manifest lists those substations
