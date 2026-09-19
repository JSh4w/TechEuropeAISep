## Purpose

Extends the capacity proposal to larger batteries by using grid-level substations at 132 kV when a primary substation cannot carry the requested size.

## ADDED Requirements

### Requirement: Grid-level substations are in the snapshot
The snapshot SHALL include grid-level substations with their voltage, position, headroom, and provenance, validated the same way as primary substations.

#### Scenario: Load
- **WHEN** the snapshot loads
- **THEN** grid-level substations are available with dataset id and snapshot date

### Requirement: Large requests use grid-level connection
When the request's battery size exceeds the primary voltage cap, the system SHALL propose a connection at the serving or nearest grid-level substation, label it as 132 kV, and cap the ceiling at 100 MW.

#### Scenario: 80 MW request
- **WHEN** the request is for 80 MW and a grid-level substation lies within 5 km
- **THEN** the proposal is at that substation, labelled 132 kV, with a ceiling of at most 100 MW

#### Scenario: Above the cap
- **WHEN** the request is for 150 MW
- **THEN** the result is not viable and says sites above 100 MW are out of scope

### Requirement: Missing coverage is stated
When no grid-level substation lies within 5 km of the position, the system SHALL return not viable with a message that no grid-level data covers the site, and SHALL NOT fall back to a primary substation.

#### Scenario: No coverage
- **WHEN** the request is for 80 MW and no grid-level substation is within 5 km
- **THEN** the result says no grid-level data covers the site

### Requirement: Small requests are unchanged
When the request has no battery size, or a size within the primary voltage cap, the system SHALL behave exactly as before.

#### Scenario: 20 MW request
- **WHEN** the request is for 20 MW
- **THEN** the result is the same as without this feature
