## Purpose

Estimates the capital and operating cost of a battery site from documented assumptions, including grid connection cost from route length and the proposed Ofgem oversubscription fee.

## ADDED Requirements

### Requirement: Every cost input is documented
The system SHALL read every cost input from an assumptions file where each value has a unit, a source and a date. The system SHALL NOT use an undocumented number.

#### Scenario: Missing assumption
- **WHEN** a required cost input is missing from the file
- **THEN** the stage fails with an error that names the missing key

### Requirement: Capital and operating cost per duration
The system SHALL compute capital cost and annual operating cost for 2-hour, 4-hour and 8-hour batteries at the confirmed capacity, from the battery cost per MWh, balance-of-plant cost, and connection cost.

#### Scenario: Cost grows with duration
- **WHEN** costs are computed for 20 MW
- **THEN** capital cost at 8 hours is higher than at 4 hours, which is higher than at 2 hours

### Requirement: Connection cost comes from route length
The system SHALL cost a 33 kV underground connection at £500,000 to £700,000 per km over the distance to the substation, and report a low and a high figure. When the land analysis reports hard surfaces or crossings of railways, rivers or major roads, the system SHALL apply the documented uplift and state that it did. The 132 kV rate SHALL be recorded in the assumptions file and SHALL NOT be used.

#### Scenario: One kilometre
- **WHEN** the distance to the substation is 1 km
- **THEN** connection cost is £500,000 to £700,000

#### Scenario: Three kilometres
- **WHEN** the distance is 3 km
- **THEN** connection cost is £1,500,000 to £2,100,000

#### Scenario: Crossing uplift
- **WHEN** the land analysis reports a railway crossing
- **THEN** the documented uplift is applied and the artifact says so

### Requirement: Proposed Ofgem fee is a marked CAPEX line
The system SHALL include the proposed Oversubscribed Technologies Commitment Fee as a CAPEX line at £3,000 to £25,000 per MW, labelled "proposed, not in force". The fee SHALL be active when the documented oversubscription figure is above 50%, inactive when below 25%, and inactive when between with no earlier state.

#### Scenario: Fee active
- **WHEN** oversubscription is 60% and capacity is 20 MW
- **THEN** the fee line is £60,000 to £500,000, labelled proposed

#### Scenario: Fee inactive
- **WHEN** oversubscription is 20%
- **THEN** no fee line is included and the artifact says the fee is inactive

#### Scenario: Between thresholds
- **WHEN** oversubscription is 40%
- **THEN** the fee line is inactive
