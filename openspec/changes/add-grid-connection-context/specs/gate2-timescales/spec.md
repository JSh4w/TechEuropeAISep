## Purpose

Tells the developer where a new application would sit in the parent grid supply point's queue and how long comparable connections have taken.

## ADDED Requirements

### Requirement: Queue at the parent grid supply point is reported
The system SHALL report the number of projects and the total MW queued at the parent grid supply point, grouped by status, and the position a new application would take, which is after all existing projects.

#### Scenario: Queue with projects
- **WHEN** the parent grid supply point has 12 queued projects
- **THEN** the report states 12 projects and a new application position of 13

#### Scenario: Grid supply point unknown
- **WHEN** the serving substation has no known parent grid supply point
- **THEN** the report says queue data is unavailable and the run continues

### Requirement: Indicative timescales come from past outcomes
The system SHALL report a range of months, from the lower to the upper quartile, between application and offer or energisation, taken from modification-application outcomes at the parent grid supply point, with the number of records used. With fewer than 3 records, the system SHALL mark the estimate as low confidence.

#### Scenario: Enough records
- **WHEN** 8 outcome records exist
- **THEN** the report gives the quartile range and states 8 records

#### Scenario: Too few records
- **WHEN** 2 outcome records exist
- **THEN** the estimate is marked low confidence

### Requirement: Grid stage output is filled
The grid connection stage output SHALL set the queue position and the median indicative months from these figures, and SHALL return one artifact per figure with dataset and snapshot date as the source.

#### Scenario: Grid output
- **WHEN** the grid connection stage completes with data available
- **THEN** its output has a queue position and median months, and each figure has an artifact
