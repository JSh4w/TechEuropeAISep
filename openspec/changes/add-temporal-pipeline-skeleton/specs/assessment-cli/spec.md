## Purpose

Gives the demo presenter a command-line way to start an assessment, confirm the site, and read the result with its evidence.

## ADDED Requirements

### Requirement: Start an assessment from a link or postcode
The CLI SHALL provide a `start` command that takes a property link or a `--postcode`, plus optional `--battery-mw`, `--budget-gbp` and `--flexible`. It SHALL start a run and print the run id. By default it SHALL stay attached and guide the user through the whole run. With `--detach` it SHALL print the run id and exit.

#### Scenario: Attached run from a link
- **WHEN** the user runs `start <url> --battery-mw 20`
- **THEN** the CLI shows stage progress until the run pauses for confirmation

#### Scenario: Run from a postcode
- **WHEN** the user runs `start --postcode "SW1A 1AA"`
- **THEN** a run starts with that postcode

#### Scenario: Detached run
- **WHEN** the user runs `start <url> --detach`
- **THEN** the CLI prints the run id and exits immediately

#### Scenario: No site given
- **WHEN** the user runs `start` with neither a link nor a postcode
- **THEN** the CLI prints a validation error and starts no run

### Requirement: Confirm the site at a prompt
When the run pauses, the CLI SHALL show the capacity proposal (serving substation, connection voltage, firm and ceiling capacity, which direction limits it) and the boundary artifacts, then ask the user to confirm or reject. The prompt SHALL offer the recommended capacity as the default and accept a different capacity within the allowed range. With `--yes`, the CLI SHALL confirm the defaults without asking.

#### Scenario: User accepts the default
- **WHEN** the run pauses and the user answers "y" and presses enter at the capacity prompt
- **THEN** the CLI confirms the recommended capacity and continues showing progress

#### Scenario: User changes the capacity
- **WHEN** the user enters a capacity above the allowed range
- **THEN** the CLI shows the allowed range and asks again

#### Scenario: User answers no
- **WHEN** the run pauses and the user answers "n"
- **THEN** the CLI rejects the site and prints that the run was rejected

#### Scenario: Confirm a detached run
- **WHEN** the user runs `confirm <run-id>` for a paused run
- **THEN** the run continues with defaults; `--capacity-mw N` sets a capacity and `--reject` rejects it

### Requirement: Show the result and its evidence
The CLI SHALL provide a `result` command that prints the report and the path of the run's artifact folder. After an attached run completes, `start` SHALL print the same output.

#### Scenario: Completed run
- **WHEN** the user runs `result <run-id>` for a completed run
- **THEN** the CLI prints the verdict, the capacity range, the duration comparison, the findings with their artifact ids, and the artifact folder path

#### Scenario: Unfinished run
- **WHEN** the user runs `result <run-id>` for a run that is still running
- **THEN** the CLI prints the run's current status and stages and exits without a report

#### Scenario: Out-of-area or non-viable run
- **WHEN** the user runs `result <run-id>` for an out-of-area or non-viable run
- **THEN** the CLI prints the run's message (for example a hint to re-run with `--flexible`)

### Requirement: Clear error when Temporal is unavailable
The CLI SHALL print a short message that tells the user to start the Temporal server when it cannot connect.

#### Scenario: Server down
- **WHEN** the Temporal server is not running and the user runs any command
- **THEN** the CLI prints a message naming `temporal server start-dev` and exits with a non-zero code
