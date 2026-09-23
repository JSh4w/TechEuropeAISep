## ADDED Requirements

### Requirement: The cable route follows roads where possible
Every capacity result with a serving substation SHALL include the substation's position and a cable route from the site to it: its distance, its path, and its method. The method SHALL be `road` when a road route was found, and `straight_line` otherwise. A failure to find a road route SHALL NOT fail the capacity check.

#### Scenario: Road route found
- **WHEN** a capacity check finds a serving substation and the routes service returns a route
- **THEN** the result has a `road` route whose path starts at the site and ends at the substation, and whose distance is at least the straight-line distance

#### Scenario: Pin on the far side of the plot
- **WHEN** the pin sits in a registered title and the substation lies beyond the opposite edge of it
- **THEN** the road route starts at the point on the title's edge nearest the substation, the path runs pin, that edge point, the road, the substation, and the distance includes the leg across the plot

#### Scenario: No key or service failure
- **WHEN** no routes key is configured, or the routes service errors or times out
- **THEN** the result has a `straight_line` route with the straight-line distance, and an artifact says why

### Requirement: The cost model prices the cable on the route
The financial model SHALL price the connection cable on the route distance when the capacity result has a route, and on the straight-line distance otherwise. Its cost artifact SHALL name the distance used.

#### Scenario: Road route priced
- **WHEN** the capacity result has a 0.85 km road route and a 0.57 km straight-line distance
- **THEN** the cable cost is computed on 0.85 km

### Requirement: The map shows the route and says what it is
The map SHALL draw the cable from the pin to the serving substation's real position: along the route path when the method is `road`, as a dashed straight line otherwise. The legend SHALL say which, with the distance. Substation popups SHALL label their distance as a straight-line distance.

#### Scenario: Road route drawn
- **WHEN** the capacity result has a `road` route
- **THEN** the map draws a solid line along the route and the legend reads "Cable route by road" with its distance

#### Scenario: Straight line drawn
- **WHEN** the capacity result has no route or a `straight_line` route
- **THEN** the map draws a dashed straight line and the legend reads "Cable run, straight line"

#### Scenario: Dragging the pin
- **WHEN** the user drags the pin
- **THEN** the cable is drawn as a dashed straight line from the pin until the new capacity result arrives
