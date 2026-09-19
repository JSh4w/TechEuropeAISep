## Purpose

Defines the typed data that flows between assessment stages, including the `Artifact` that makes every claim explainable. Every stage input and output is validated against these models.

## ADDED Requirements

### Requirement: Assessment request identifies the site and the user's intent
The system SHALL accept an assessment request with a property link, a UK postcode, or both. It SHALL reject a request with neither. The request MAY also carry a target battery size in MW, a budget in GBP, and a flexible-connection flag that defaults to off.

#### Scenario: Link only
- **WHEN** a request is created with a property URL and no postcode
- **THEN** the request validates

#### Scenario: Postcode only
- **WHEN** a request is created with the postcode "SW1A 1AA" and no link
- **THEN** the request validates

#### Scenario: No site given
- **WHEN** a request is created with neither a link nor a postcode
- **THEN** validation fails before any stage runs

#### Scenario: Invalid link
- **WHEN** a request is created with a property link that is not a URL
- **THEN** validation fails before any stage runs

### Requirement: Artifact records evidence for a claim
The system SHALL represent each piece of evidence as an `Artifact` with: a unique id, the stage that produced it, a claim, a confidence between 0 and 1, and the name of the model or data source that produced it. An artifact SHALL carry at least one piece of evidence: a source URL, a file path, or an image path.

#### Scenario: Artifact with a source link
- **WHEN** an artifact is created with a claim, a source URL, confidence 0.8 and a model name
- **THEN** it validates

#### Scenario: Artifact without evidence
- **WHEN** an artifact is created with no source URL, file path or image path
- **THEN** validation fails

#### Scenario: Confidence out of range
- **WHEN** an artifact is created with confidence 1.4
- **THEN** validation fails

### Requirement: Every stage has typed input and output
The system SHALL define a validated input model and output model for each stage: location, capacity, title, grid connection, site and land, market, financial, planning, and synthesis. Each stage output SHALL include the list of artifacts the stage produced.

#### Scenario: Stage output carries artifacts
- **WHEN** any stage returns its output
- **THEN** the output contains a list of artifacts, each tagged with that stage's name

#### Scenario: Malformed stage output
- **WHEN** a stage returns data that does not match its output model
- **THEN** the run fails at that stage with a validation error

### Requirement: Capacity proposal states a range and what limits it
The capacity stage output SHALL state: whether the site is viable (with a message when it is not), whether it is out of area, the serving substation, the connection voltage, a firm capacity in MW, a ceiling capacity in MW that is at least the firm capacity, a recommended capacity, and which direction (import or export) limits it.

#### Scenario: Ceiling below firm
- **WHEN** a capacity output has a ceiling lower than its firm capacity
- **THEN** validation fails

#### Scenario: Out-of-area site
- **WHEN** a capacity output is marked out of area
- **THEN** it is also marked not viable, has a message, and validates with no substation and zero capacities

#### Scenario: Not viable
- **WHEN** a capacity output is marked not viable
- **THEN** it carries a message that says why

### Requirement: Confirmed site carries position, capacity and boundary
The system SHALL represent the user's confirmation as a confirmed site with a map position, a capacity in MW, and the title boundary. The footprint geometry is optional. The capacity SHALL NOT exceed the ceiling of the capacity proposal, and SHALL NOT exceed the firm capacity unless the request enabled flexible connection.

#### Scenario: Capacity above ceiling
- **WHEN** a confirmed site has capacity above the proposal's ceiling
- **THEN** validation fails

#### Scenario: Capacity above firm without flexible connection
- **WHEN** flexible connection is off and the confirmed capacity exceeds the firm capacity
- **THEN** validation fails

#### Scenario: Capacity above firm with flexible connection
- **WHEN** flexible connection is on and the confirmed capacity is between firm and ceiling
- **THEN** it validates

### Requirement: Financial output compares three durations
The financial stage output SHALL contain one case each for 2-hour, 4-hour and 8-hour batteries, with capital cost, net present value and internal rate of return per case.

#### Scenario: Three cases
- **WHEN** the financial stage completes
- **THEN** its output has exactly the durations 2, 4 and 8
