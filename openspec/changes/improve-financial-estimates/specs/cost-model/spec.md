## ADDED Requirements

### Requirement: One agreed figure per cost input
The system SHALL use exactly one figure for the mid case of each cost input, and that figure SHALL equal the `mid` of the input's documented low/mid/high range. An assumption entry whose single value differs from its range midpoint SHALL fail validation with an error that names the key.

#### Scenario: Battery cost is consistent
- **WHEN** the battery cost range is £110k / £140k / £180k per MWh
- **THEN** the mid case uses £140k per MWh

#### Scenario: Inconsistent entry
- **WHEN** an entry has value £250k and mid £140k
- **THEN** loading the assumptions fails and the error names the key

### Requirement: Embedded export credit
The system SHALL add an annual Embedded Export Tariff credit per MW for sites below 100 MW, from a documented national figure with a source and tariff year. The low bound SHALL be zero, because the credit depends on exporting during the Triad peak periods. For sites at or above 100 MW, the system SHALL add no credit and SHALL say in the artifact that transmission charges are not modelled.

#### Scenario: Embedded site
- **WHEN** a 20 MW site is assessed and the documented tariff is £3.05 per kW
- **THEN** the mid case includes a credit of £61,000 per year, and the artifact names the tariff year

#### Scenario: Large site
- **WHEN** a 120 MW site is assessed
- **THEN** no credit is applied and the artifact says transmission charges are not modelled

### Requirement: Development cost and land lease
The system SHALL add a fixed development cost per project (planning, legal, grid application) to capital cost. The system SHALL add an annual land lease cost equal to the documented rate per acre times the site's reserved acres.

#### Scenario: Larger sites cost less per MW
- **WHEN** capital cost is computed for 5 MW and for 40 MW at the same duration and distance
- **THEN** capital cost per MW at 40 MW is lower than at 5 MW

#### Scenario: Land lease follows footprint
- **WHEN** the reserved area is 3 acres and the documented rate is £25,000 per acre per year
- **THEN** annual operating cost includes £75,000 for land
