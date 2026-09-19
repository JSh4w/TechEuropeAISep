## Purpose

Proposes how much battery capacity a UK location could connect to the UKPN network, where it would connect, and what limits it. The proposal is deterministic and explainable, and it corrects for three ways the published headroom data misleads.

## ADDED Requirements

### Requirement: Serving substation is found by containment
The system SHALL select the serving primary substation as the one whose distribution-area polygon contains the position. It SHALL NOT use the nearest substation for this choice. The result SHALL be presented as the predicted point of connection, not a choice.

#### Scenario: Nearest is not serving
- **WHEN** a position lies inside substation A's area but is closer to substation B
- **THEN** substation A is the predicted point of connection

### Requirement: Out-of-area positions are reported clearly
The system SHALL report a position that lies in no UKPN distribution area as out of area, with a message that says the tool covers UKPN areas only.

#### Scenario: Position outside UKPN
- **WHEN** the position is in Manchester
- **THEN** the result is out of area and not viable, with no capacity

### Requirement: Headroom accounts for the accepted queue
The system SHALL compute effective headroom per direction by subtracting accepted connection offers from available capacity. Export headroom SHALL add reverse power flow capacity when the substation's minimum demand is negative. The published Red/Amber/Green values SHALL NOT be used to compute capacity.

#### Scenario: Queue subtracted
- **WHEN** a substation has 20 MW available import and 8 MW of accepted load offers
- **THEN** its effective import headroom is 12 MW

#### Scenario: Reverse power flow
- **WHEN** minimum demand is negative and reverse power flow capacity is 3 MW
- **THEN** 3 MW is added to the export headroom

#### Scenario: Green does not mean connectable
- **WHEN** a substation is published as Green with 2 MW effective headroom
- **THEN** the proposal reports 2 MW

### Requirement: Capacity is reported as a range with seasons
The system SHALL report a firm capacity (no curtailment) and a ceiling capacity (curtailment rises across the range). Firm capacity SHALL be the lowest across winter and summer, and the result SHALL name the constraining season.

#### Scenario: Summer constrains
- **WHEN** summer firm capacity is lower than winter
- **THEN** the result names summer as the binding season

#### Scenario: Range
- **WHEN** a proposal is made
- **THEN** the ceiling is at least the firm capacity

### Requirement: Size is limited by the tighter direction
The system SHALL propose a size that does not exceed the smaller of import and export capacity, and SHALL name which direction limits it.

#### Scenario: Import binds
- **WHEN** import headroom is 6 MW and export headroom is 10 MW
- **THEN** the size is at most 6 MW and the binding direction is import

### Requirement: Connection voltage caps the size
The system SHALL cap every proposal at what its connection voltage can carry: about 8 MW at 11 kV and below, about 50 MW at 33 kV and 66 kV. The cap SHALL apply independently of headroom. The connection voltage SHALL be the substation's registered point of connection voltage.

#### Scenario: Headroom above the voltage cap
- **WHEN** an 11 kV substation has 30 MW of headroom
- **THEN** the proposed ceiling is at most 8 MW

### Requirement: Sites below the 5 MW floor are not viable
The system SHALL treat a site as viable only if it can offer at least 5 MW. With flexible connection off, the test SHALL use firm capacity. With flexible connection on, it SHALL use the ceiling. When the site fails only the firm test, the result SHALL be not viable and the message SHALL state the firm figure and the ceiling figure and suggest enabling flexible connection. The recommended capacity SHALL be the firm capacity when flexible connection is off, and the ceiling when it is on.

#### Scenario: Firm below floor, ceiling above
- **WHEN** flexible connection is off, firm capacity is 3 MW and ceiling is 9 MW
- **THEN** the result is not viable and the message mentions 3 MW, 9 MW and flexible connection

#### Scenario: Flexible connection on
- **WHEN** flexible connection is on and the ceiling is 9 MW
- **THEN** the result is viable with a recommended capacity of 9 MW

#### Scenario: Ceiling below floor
- **WHEN** the ceiling is 4 MW
- **THEN** the result is not viable regardless of flexible connection

### Requirement: Distance penalises ranking beyond 1 km
The system SHALL rank the serving substation and up to four alternates within 5 km by capacity weighted by distance, with a penalty that is zero up to 1 km and rises steeply beyond it. Options beyond 1 km SHALL be shown and flagged marginal, not hidden. Distance SHALL be reported for each option.

#### Scenario: Marginal option shown
- **WHEN** the best alternate is 3 km away
- **THEN** it appears in the result flagged as marginal

### Requirement: Context checks do not drive the verdict
The system SHALL report, as separate artifacts: the published Red/Amber/Green values, the status of the parent grid supply point, and the Transmission Impact Assessment threshold (1 MW or 5 MW) of the substation. None of them SHALL change the capacity result.

#### Scenario: RAG shown as context
- **WHEN** a proposal is made
- **THEN** the published RAG values appear in an artifact that says they are context only

### Requirement: Every figure is an artifact with provenance
The system SHALL return artifacts that state each key figure (serving substation, effective headroom by direction, firm and ceiling capacity, binding direction, voltage cap) with the dataset id and snapshot date as the source.

#### Scenario: Provenance
- **WHEN** a proposal is made
- **THEN** each artifact names its source dataset and the snapshot date

### Requirement: Checks are logged
The system SHALL append one record per capacity check to a log file, with the position, the result, and the snapshot date. The log SHALL NOT be read during a run.

#### Scenario: Check logged
- **WHEN** a capacity proposal completes or reports out of area
- **THEN** one new line is appended to the log

### Requirement: Proposal is fast
The proposal SHALL complete in under 1 second from a loaded snapshot.

#### Scenario: Timing
- **WHEN** a proposal is requested for a position in the snapshot area
- **THEN** it returns in under 1 second
