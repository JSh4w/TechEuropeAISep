## ADDED Requirements

### Requirement: Area outside the screening radius is dulled
The map SHALL visually de-emphasize (dim/mask) the area beyond the 2 km screening radius from the postcode position, so the region the pin cannot be dragged into reads as out of scope. The area inside the radius SHALL remain unmasked. This is a visual aid only; it SHALL NOT be the mechanism that enforces the pin's movement limit.

#### Scenario: Default view
- **WHEN** the map loads at the postcode position
- **THEN** the area outside the 2 km radius appears dulled and the area inside does not

#### Scenario: Dragging within range
- **WHEN** the user drags the pin to a position still inside the 2 km radius
- **THEN** the dulled area is unchanged and the pin remains in the undulled region

#### Scenario: Dragging to the limit
- **WHEN** the user drags the pin to the 2 km boundary
- **THEN** the pin sits at the edge of the undulled area, matching the existing 2 km clamp behavior

### Requirement: Reserved Compound square stays within the screening radius
The Reserved Compound square (the footprint sized to the recommended capacity) SHALL remain entirely within the 2 km screening radius at every position the pin can occupy. The pin's movement limit SHALL account for the square's size, not just its center point, both while dragging and after a capacity change.

#### Scenario: Dragging toward the boundary
- **WHEN** the user drags the pin toward the 2 km boundary with a capacity selected whose Reserved Compound square has half-diagonal D
- **THEN** the pin stops at (2 km − D) from the postcode position, so no corner of the square crosses the boundary

#### Scenario: Capacity increases while pin is near its limit
- **WHEN** the user increases capacity while the pin sits near its current clamp limit
- **THEN** the pin (and the square) is pulled back in as needed so the square stays within the 2 km boundary, without requiring a new drag
