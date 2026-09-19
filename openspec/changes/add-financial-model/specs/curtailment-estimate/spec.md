## Purpose

Estimates how much revenue a flexible connection loses to curtailment, using only the hours where the grid constraint and the battery's dispatch actually overlap.

## ADDED Requirements

### Requirement: Load duration curve is synthesised
The system SHALL build a load duration curve by scaling a documented standard UK distribution demand profile between the substation's published maximum and minimum demand.

#### Scenario: Curve bounds
- **WHEN** a curve is built for a substation with maximum 40 MW and minimum 10 MW
- **THEN** its highest value is 40 MW and its lowest is 10 MW

### Requirement: Haircut applies to overlap only
The system SHALL apply the curtailment haircut only to hours that are both constrained and hours the battery would dispatch. The battery SHALL be assumed to charge at low demand and discharge at peak demand. The estimate SHALL be labelled as a documented assumption, not measured data.

#### Scenario: Overlap is smaller than constrained hours
- **WHEN** the constrained hours are 20% of the year
- **THEN** the curtailment percentage applied is lower than 20%

#### Scenario: Assumption is stated
- **WHEN** a curtailment figure is produced
- **THEN** its artifact states the demand profile used and that the figure is an assumption

### Requirement: Curtailment applies only above firm capacity
The system SHALL apply zero curtailment when the confirmed capacity is at or below the firm capacity.

#### Scenario: Within firm capacity
- **WHEN** the confirmed capacity equals the firm capacity
- **THEN** curtailment is 0%

#### Scenario: Between firm and ceiling
- **WHEN** the confirmed capacity is between firm and ceiling
- **THEN** curtailment is above 0% and rises as capacity approaches the ceiling
