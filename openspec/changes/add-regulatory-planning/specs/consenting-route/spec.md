## Purpose

States how a battery site in England is consented, names the deciding authority, and lists planning risks, so a developer does not plan for a route that does not apply.

## ADDED Requirements

### Requirement: Route is local planning authority consent
For a position in England, the system SHALL state that standalone battery energy storage was removed from the Nationally Significant Infrastructure regime in England in 2020, that any size is consented by the local planning authority, and that no Development Consent Order threshold applies. The route SHALL NOT change with capacity.

#### Scenario: Small site
- **WHEN** the confirmed capacity is 6 MW
- **THEN** the route is local planning authority consent

#### Scenario: Large site
- **WHEN** the confirmed capacity is 49 MW
- **THEN** the route is still local planning authority consent

### Requirement: The authority is named
The system SHALL name the local planning authority for the position. If the authority cannot be found, the system SHALL say so and keep the route statement.

#### Scenario: Authority found
- **WHEN** the position is in a known district
- **THEN** the output names that district's planning authority

#### Scenario: Authority unknown
- **WHEN** the lookup returns nothing
- **THEN** the output says the authority is unknown and the run continues

### Requirement: Positions outside England are flagged
When the position is outside England, the system SHALL say the England-specific route does not apply.

#### Scenario: Outside England
- **WHEN** the lookup places the position in Wales
- **THEN** the output says the England route does not apply

### Requirement: Planning risks cite evidence
The system SHALL list planning risks drawn from the land analysis constraints, and each risk SHALL cite the artifact that reports it.

#### Scenario: Cited risk
- **WHEN** the land analysis reports a Green Belt constraint
- **THEN** the risk list includes it and cites that artifact
