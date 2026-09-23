## ADDED Requirements

### Requirement: Demand bounds come from the serving substation
The system SHALL scale the load duration curve between the serving substation's published maximum and minimum demand, from whichever supported network operator (UKPN, NGED, SSEN, SPEN, NPg) publishes them. Figures in MVA SHALL be converted to MW with the documented power factor.

#### Scenario: Operator publishes both bounds
- **WHEN** the serving substation publishes a maximum of 30 MVA and a minimum of 6 MVA
- **THEN** the curve is scaled between those values converted to MW, and the artifact names the substation and dataset

#### Scenario: Two sites differ
- **WHEN** two sites are served by substations with different published demand
- **THEN** their curtailment estimates differ at the same capacity and firm headroom

### Requirement: Missing demand bounds are flagged
When the operator publishes a maximum but no minimum, the system SHALL derive the minimum from the maximum with a documented ratio. When neither is published, the system SHALL use documented default bounds taken from the median of published GB primary substations. In both cases the artifact SHALL say which figures are assumed, and its confidence SHALL be lower than when both bounds are published.

#### Scenario: No published demand
- **WHEN** the serving substation publishes no demand figures
- **THEN** the default bounds are used and the artifact says "assumed" and names the default values
