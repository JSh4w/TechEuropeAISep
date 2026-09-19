## Purpose

Lets the user see where a battery could connect, position a generated footprint on the intended site, choose a capacity, and confirm, all on one map.

## ADDED Requirements

### Requirement: Ranked substations are shown
The map SHALL plot the serving substation and the ranked alternates with their effective headroom, and SHALL flag options beyond 1 km as marginal.

#### Scenario: Options shown
- **WHEN** the run is paused for confirmation
- **THEN** the map shows each option with its headroom and marks marginal ones

### Requirement: The footprint is generated, the user positions it
The map SHALL show a footprint sized to the recommended capacity. The user SHALL be able to move it but SHALL NOT need to draw it.

#### Scenario: Move the footprint
- **WHEN** the user drags the footprint to a new place
- **THEN** its size is unchanged and its position is updated

### Requirement: Registered boundaries are overlaid where available
The map SHALL overlay HM Land Registry INSPIRE polygons where they exist. When none exist, the map SHALL work without them.

#### Scenario: No polygons
- **WHEN** the area has no INSPIRE polygons
- **THEN** the map shows no overlay and no error

### Requirement: Size slider
The map page SHALL show a slider that resizes the footprint and shows the capacity in MW and the area in acres at all times. It SHALL open at the recommended capacity. With flexible connection off, it SHALL run from 5 MW to the firm capacity. With it on, it SHALL run to the ceiling, and moving past the firm capacity SHALL show curtailment rising. It SHALL NOT allow a capacity above the site's maximum.

#### Scenario: Firm range
- **WHEN** flexible connection is off, firm is 9 MW and the ceiling is 14 MW
- **THEN** the slider runs from 5 to 9 MW

#### Scenario: Flexible range
- **WHEN** flexible connection is on
- **THEN** the slider runs from 5 to 14 MW and shows curtailment above 9 MW

### Requirement: Flexible connection toggle
The page SHALL show a flexible-connection toggle that is off by default. Its state SHALL be sent with the decision and held in the run state, not only in the browser. When no capacity is viable with the toggle off, the page SHALL offer the toggle as the next step.

#### Scenario: Default off
- **WHEN** the page loads
- **THEN** the toggle is off

#### Scenario: Empty firm view
- **WHEN** the run ended not viable with a message about flexible connection
- **THEN** the page offers to start again with the toggle on

### Requirement: Moving the pin re-checks capacity
The user SHALL be able to place the pin no more than 2 km from the postcode position. When the pin moves, the page SHALL re-run the capacity check at the new position and show the new proposal. If the serving substation changes, the page SHALL say so.

#### Scenario: Pin beyond limit
- **WHEN** the user drags the pin 3 km away
- **THEN** the pin returns to the 2 km limit

#### Scenario: New substation
- **WHEN** the moved pin lies in a different substation's area
- **THEN** the page shows the new substation and its capacity

### Requirement: Confirming sends the site
Confirming SHALL send the position, the capacity, the footprint and the toggle state as the decision. If the position differs from the proposal's, the run SHALL re-check capacity at that position before continuing.

#### Scenario: Confirm
- **WHEN** the user confirms
- **THEN** the run continues with that position, capacity and footprint
