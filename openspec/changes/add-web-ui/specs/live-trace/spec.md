## Purpose

Shows the user what the agents are doing while a run is in progress, and lets the page reconnect without losing or repeating steps.

## ADDED Requirements

### Requirement: Progress is written to an append-only event log
The system SHALL append an event for each stage start, stage end, and agent progress message to a log file in the run's folder. Each event SHALL have an increasing id, a time, a stage, and a message. The system SHALL NOT edit or delete earlier events.

#### Scenario: Stage events
- **WHEN** a stage starts and ends
- **THEN** two events are appended with increasing ids

#### Scenario: Agent step
- **WHEN** an agent stage reports an intermediate step
- **THEN** an event with that message is appended

### Requirement: Events stream over SSE
The system SHALL stream a run's events to the browser as server-sent events, starting from the beginning, and SHALL end the stream after the final event.

#### Scenario: Live stream
- **WHEN** a client opens the stream during a run
- **THEN** it receives past events and then new events as they happen

### Requirement: Reconnect resumes without loss
When a client reconnects with a last event id, the system SHALL send only events after that id, with none missing and none repeated.

#### Scenario: Resume
- **WHEN** a client reconnects with last event id 7
- **THEN** the first event it receives has id 8

### Requirement: No extra store or broker
The system SHALL NOT need Redis or any message broker for the trace. The log file is the only store.

#### Scenario: No broker
- **WHEN** the trace runs on a machine with no Redis
- **THEN** it works

### Requirement: Failures in tracing never fail a run
A failure to write an event, or any error in developer-facing Logfire instrumentation, SHALL NOT block or fail a run. The system SHALL keep the user-facing trace independent of Logfire.

#### Scenario: Logfire error
- **WHEN** Logfire raises an error during a stage
- **THEN** the stage completes and the user-facing trace continues

#### Scenario: Unwritable log
- **WHEN** an event cannot be written
- **THEN** the run continues and a warning is logged
