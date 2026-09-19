## Purpose

Lets anyone see a full Bessible run with no keys, no sign-in and no LLM or Temporal calls, by replaying a previously recorded real run.

## ADDED Requirements

### Requirement: Record a real run
The system SHALL provide a recorder that captures one real run into `data/demo/<slug>/`: the request, trace events with relative timings, a status snapshot for each stage transition, the site-confirmation decision, and the result. Recordings SHALL contain no API keys or credentials.

#### Scenario: Record
- **WHEN** the recorder is run against a completed real run
- **THEN** `data/demo/<slug>/` contains the request, timed events, status snapshots, decision and result, and a scan finds no key material

### Requirement: Keyless replay
Replay routes SHALL be public and SHALL serve a recording without Temporal, Firebase auth, or any model or network call. Replay run ids SHALL be prefixed `demo-` and SHALL never resolve to a real run.

#### Scenario: Replay with no keys
- **WHEN** a visitor with no keys starts the demo run
- **THEN** status, trace events and the final report stream from the recording with the recorded pacing

#### Scenario: Confirmation gate
- **WHEN** the replay reaches the human-in-the-loop site confirmation step
- **THEN** it pauses until the visitor submits a decision, accepts any decision, and then continues to the recorded result

### Requirement: Demo entry points and labelling
The first-load keys modal and the landing view SHALL offer **View demo run**, and the UI SHALL label a replay as a recording rather than live output.

#### Scenario: Demo button
- **WHEN** a visitor clicks **View demo run**
- **THEN** the replay starts and the UI shows that it is a recorded example
