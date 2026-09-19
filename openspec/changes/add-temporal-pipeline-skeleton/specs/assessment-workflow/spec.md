## Purpose

Runs a property assessment as a durable, resumable pipeline of stages, pausing for human confirmation of the site. Every stage can be replaced independently without changing how the pipeline runs.

## ADDED Requirements

### Requirement: Stages run in a fixed order with parallel groups
The system SHALL run stages in this order: location, capacity, title, human confirmation, then grid connection, site and land, and market in parallel, then financial and planning in parallel, then synthesis. Each stage SHALL receive the outputs of the earlier stages it depends on. A stage SHALL NOT start before all its dependencies complete.

#### Scenario: Full run
- **WHEN** an assessment starts and the user confirms the site
- **THEN** all stages run in the stated order and the run completes with a report

#### Scenario: Parallel group
- **WHEN** the user confirms the site
- **THEN** grid connection, site and land, and market start without waiting for each other

#### Scenario: Dependencies respected
- **WHEN** grid connection and market are complete but site and land is not
- **THEN** the planning stage has not started

#### Scenario: Confirmed site feeds later stages
- **WHEN** the user confirms position and capacity
- **THEN** every later stage receives that confirmed position and capacity

### Requirement: Pipeline works end-to-end with placeholder stages
The system SHALL ship with a placeholder implementation of every stage that returns realistic fixed artifacts. Replacing one stage's implementation SHALL NOT require changes to the workflow, worker, or other stages.

#### Scenario: Run with only placeholders
- **WHEN** an assessment runs with no real stage implemented
- **THEN** it completes and the report contains artifacts from every stage

#### Scenario: Replace one stage
- **WHEN** a teammate replaces the site and land implementation with one that has the same input and output models
- **THEN** the run completes and only site and land artifacts change

### Requirement: Human confirms the site before analysis
The system SHALL pause after title boundaries and wait for a confirm or reject decision. While paused, the system SHALL expose the capacity proposal and boundary artifacts for the user to review. The decision MAY set a position and a capacity; omitted values default to the proposal. The system SHALL reject a decision whose capacity is out of range and keep waiting. The system SHALL NOT run any analysis stage until the user confirms.

#### Scenario: User confirms with defaults
- **WHEN** the run is paused and the user confirms without a capacity
- **THEN** the run continues using the recommended capacity

#### Scenario: User confirms with a capacity
- **WHEN** the run is paused and the user confirms 12 MW within the allowed range
- **THEN** later stages receive a confirmed capacity of 12 MW

#### Scenario: Capacity out of range
- **WHEN** the run is paused and the user confirms a capacity above the ceiling
- **THEN** the system returns an error to the user and the run stays paused

#### Scenario: User rejects
- **WHEN** the run is paused and the user rejects
- **THEN** the run ends with status `rejected`, no analysis stage runs, and no report is produced

#### Scenario: Run waits without a decision
- **WHEN** the run is paused and no decision arrives
- **THEN** the run stays paused and reports status `awaiting_confirmation`

### Requirement: Out-of-area and non-viable sites stop early
The system SHALL end the run with status `out_of_area` when the capacity stage reports the site is out of area, and with status `not_viable` when it reports the site is not viable. The result SHALL carry the stage's message. The system SHALL NOT ask for confirmation or run later stages.

#### Scenario: Site outside coverage
- **WHEN** the capacity stage reports out of area
- **THEN** the run ends with status `out_of_area` and no confirmation is requested

#### Scenario: Site not viable
- **WHEN** the capacity stage reports not viable with a message
- **THEN** the run ends with status `not_viable`, the result carries the message, and no confirmation is requested

### Requirement: Runs survive failures
The system SHALL retry a stage that fails with a transient error, up to 3 attempts. The system SHALL NOT retry a stage that fails validation. A run SHALL resume from the last completed stage if the worker restarts. If one stage in a parallel group fails permanently, the run SHALL fail.

#### Scenario: Transient failure
- **WHEN** a stage raises a transient error on its first attempt and succeeds on the second
- **THEN** the run completes and the stage's result is used once

#### Scenario: Validation failure
- **WHEN** a stage returns output that fails validation
- **THEN** the run fails without retrying that stage

#### Scenario: Worker restart
- **WHEN** the worker stops after the location stage completes and is restarted
- **THEN** the run continues from the capacity stage without rerunning the location stage

### Requirement: Run status is observable
The system SHALL report the current status of a run: `running`, `awaiting_confirmation`, `completed`, `rejected`, `out_of_area`, `not_viable`, or `failed`, plus the names of the stages currently running.

#### Scenario: Query mid-run
- **WHEN** a client asks for status while the market and site and land stages run
- **THEN** it receives `running` and both stage names

### Requirement: Report is built only from artifacts
The system SHALL produce a report that states a verdict and a set of findings, and includes the capacity range and the three-duration comparison. Every finding in the report SHALL cite the id of at least one artifact. The system SHALL write the report and any artifact files to a folder for that run.

#### Scenario: Findings cite artifacts
- **WHEN** the report is produced
- **THEN** each finding lists artifact ids that exist in the run's artifact list

#### Scenario: Run folder
- **WHEN** a run completes
- **THEN** the run's folder contains the report file and every file or image an artifact references
