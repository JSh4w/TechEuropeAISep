## Purpose

Estimates the annual revenue per MW that a battery could earn at each duration, from named streams with a source and date for every figure.

## ADDED Requirements

### Requirement: Revenue is a stack of named streams
The system SHALL return, for each of 2-hour, 4-hour and 8-hour batteries, revenue in GBP per MW per year for each of these streams: Capacity Market, balancing mechanism and ancillary services, and wholesale arbitrage, plus their total. Each stream SHALL have a source name and a date.

#### Scenario: Three durations, three streams
- **WHEN** the market stage completes
- **THEN** each duration has the three streams, a total that equals their sum, and a source and date per stream

### Requirement: Capacity Market revenue is de-rated by duration
The system SHALL scale Capacity Market revenue by a de-rating factor for the duration, taken from a documented table.

#### Scenario: Shorter duration earns less
- **WHEN** de-rating factors for 2 hours are lower than for 4 hours
- **THEN** the 2-hour Capacity Market revenue is lower than the 4-hour revenue at the same price

### Requirement: Failed sources fall back to fixtures
When a live source fails, the system SHALL use a cached fixture for that stream, flag it as cached, and state the fixture's date in the artifact. The run SHALL NOT fail because one source is unavailable.

#### Scenario: Source unavailable
- **WHEN** the Capacity Market source returns an error
- **THEN** the stage completes using the fixture and the artifact says "cached" with its date

### Requirement: Every figure is an artifact
The system SHALL return one artifact per stream with the source link and date, and SHALL name the source in the claim.

#### Scenario: Artifact per stream
- **WHEN** the stage completes
- **THEN** each stream has an artifact with a source link
