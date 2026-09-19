## Purpose

Adds cap-and-floor and Ultra-LDES revenue to the batteries that qualify for them, and leaves those streams out for batteries that do not.

## ADDED Requirements

### Requirement: Qualification rules are documented
The system SHALL read the qualifying rules for cap-and-floor and Ultra-LDES support from the assumptions file, each with a source and a date.

#### Scenario: Missing rule
- **WHEN** the rules for a support stream are missing from the file
- **THEN** the stage fails with an error that names the missing rule

### Requirement: Streams appear only on qualifying rows
The system SHALL include a support stream on a duration's revenue only if that duration and the confirmed capacity meet the stream's rules. A non-qualifying row SHALL omit the stream, not show it as zero.

#### Scenario: Qualifying row
- **WHEN** the 8-hour case meets the Ultra-LDES rules
- **THEN** the 8-hour revenue includes an Ultra-LDES stream

#### Scenario: Non-qualifying row
- **WHEN** the 2-hour case does not meet the rules
- **THEN** the 2-hour revenue has no Ultra-LDES stream

### Requirement: Support revenue is labelled
The system SHALL state in the artifact that the stream depends on a support scheme and name the scheme.

#### Scenario: Label
- **WHEN** a support stream is included
- **THEN** its artifact names the scheme
