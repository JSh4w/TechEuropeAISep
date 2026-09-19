## Purpose

Estimates how much land a battery needs, based on stored energy, and shows it where the user chooses capacity, so land is not bought before the area is understood.

## ADDED Requirements

### Requirement: Area follows energy
The system SHALL estimate reserved area as a range of 0.05 to 0.075 acres per MWh, where energy is capacity in MW times duration in hours.

#### Scenario: Two hours
- **WHEN** capacity is 10 MW and duration is 2 hours
- **THEN** the range is 1.0 to 1.5 acres

#### Scenario: Area tracks energy
- **WHEN** duration doubles at the same capacity
- **THEN** the range doubles

### Requirement: Default duration and range
The system SHALL size the footprint for 4 hours by default and SHALL also report the areas for 2 hours and 8 hours.

#### Scenario: Default
- **WHEN** a footprint is requested without a duration
- **THEN** it is sized for 4 hours and the 2-hour and 8-hour areas are also reported

### Requirement: Footprint geometry is generated
The system SHALL generate a footprint polygon as GeoJSON, centred on a given position, whose area equals the mid-range area for the chosen duration.

#### Scenario: Polygon area
- **WHEN** a footprint is generated for 1.0 acre
- **THEN** the polygon's area is 1.0 acre within 1%

### Requirement: The CLI shows the area
At the confirmation prompt, the CLI SHALL show the reserved area range for the chosen capacity and SHALL update it when the user enters a different capacity.

#### Scenario: Capacity changed
- **WHEN** the user changes the capacity from 12 MW to 8 MW
- **THEN** the shown area range is recalculated for 8 MW

### Requirement: The report states the area with evidence
The report SHALL state the reserved area for the confirmed capacity, label it a planning-grade estimate, and cite an artifact whose file records the inputs and result of the calculation.

#### Scenario: Report line
- **WHEN** a run completes
- **THEN** the report has a reserved-area finding that cites an artifact with the calculation file
