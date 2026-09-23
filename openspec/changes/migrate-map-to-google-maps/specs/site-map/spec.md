## ADDED Requirements

### Requirement: Area outside the screening radius is dulled
The map SHALL visually de-emphasize (dim/mask) the area beyond the 2 km screening radius from the postcode position, so the region the pin cannot be dragged into reads as out of scope. The area inside the radius SHALL remain unmasked. This is a visual aid only; it SHALL NOT be the mechanism that enforces the pin's movement limit, and it SHALL NOT block clicks on the map.

#### Scenario: Default view
- **WHEN** the map loads at the postcode position
- **THEN** the area outside the 2 km radius appears dulled and the area inside does not

#### Scenario: Dragging within range
- **WHEN** the user drags the pin to a position still inside the 2 km radius
- **THEN** the dulled area is unchanged and the pin remains in the undulled region

#### Scenario: Dragging to the limit
- **WHEN** the user drags the pin past the 2 km boundary
- **THEN** the pin stops inside the undulled area, with the edge of the Reserved Compound square at the boundary

### Requirement: Reserved Compound square stays within the screening radius
The Reserved Compound square (the footprint sized to the selected capacity) SHALL remain entirely within the 2 km screening radius at every position the pin can occupy. The pin's movement limit SHALL account for the square's size, not just its center point: while dragging, after a capacity change, and after the screening centre moves. Pulling the pin back in after a capacity change SHALL NOT change the capacity the user selected.

#### Scenario: Dragging toward the boundary
- **WHEN** the user drags the pin toward the 2 km boundary with a capacity selected whose Reserved Compound square has half-diagonal D
- **THEN** the pin stops at (2 km − D) from the postcode position, so no corner of the square crosses the boundary

#### Scenario: Capacity increases while pin is near its limit
- **WHEN** the user increases capacity while the pin sits near its current clamp limit
- **THEN** the pin (and the square) is pulled back in as needed so the square stays within the 2 km boundary, without requiring a new drag, and the selected capacity stays as the user set it

#### Scenario: Screening centre moves
- **WHEN** a new run starts from a moved pin and the screening centre becomes the nearest postcode
- **THEN** the pin is pulled back in as needed so the square stays within 2 km of the new centre

### Requirement: The assessed site's title boundary is drawn
When live site data is available for the pin's position, the map SHALL draw the registered title boundary, drawn above every other shape, and SHALL offer a control that zooms to it. When no title is registered there, the map SHALL say so and draw no boundary. This is how a submitted listing link shows its property boundary.

#### Scenario: Listing link submitted
- **WHEN** the user submits a listing link and the run resolves it to a position with a registered title
- **THEN** the map moves to that position and draws the title boundary with its area in hectares

#### Scenario: Zoom to title
- **WHEN** the user clicks "zoom to title"
- **THEN** the map fits the title boundary in view, zoomed in no further than today's cap (MapLibre zoom 18, Google zoom 19)

#### Scenario: No registered title
- **WHEN** the site data has no title
- **THEN** the legend shows "not registered" and no boundary is drawn

### Requirement: Missing map key shows a notice
When no Maps key is configured, or Google rejects the key, the map card SHALL show a notice naming the problem instead of a blank or broken map. The rest of the page SHALL keep working.

#### Scenario: No key
- **WHEN** `GOOGLE_MAPS_API_KEY` is not set
- **THEN** the map card shows "Map unavailable" with the name of the missing setting, and the capacity controls and telemetry still work

#### Scenario: Key rejected
- **WHEN** Google rejects the key (for example, the page's domain is not allowed)
- **THEN** the map card shows "Map unavailable" saying Google rejected the key
