## Purpose

Gives the browser the same control over an assessment run as the CLI has, plus a fast capacity check for moving the pin on the map.

## ADDED Requirements

### Requirement: Start a run
The API SHALL accept a request with a link or postcode and the optional inputs, start a run, and return its id. It SHALL reject an invalid request with field-level errors and start no run.

#### Scenario: Valid start
- **WHEN** a client posts a postcode and a battery size
- **THEN** the API returns a run id

#### Scenario: Invalid start
- **WHEN** a client posts a request with neither a link nor a postcode
- **THEN** the API returns a validation error naming the fields and starts no run

### Requirement: Read status and result
The API SHALL return the run status, and the result once the run has finished. Asking for the result of an unfinished run SHALL return a clear "not finished" response with the status.

#### Scenario: Unfinished result
- **WHEN** a client asks for the result while the run is paused
- **THEN** the API says the run is not finished and includes the status

### Requirement: Send the site decision
The API SHALL forward the confirm or reject decision to the run. An out-of-range capacity SHALL return an error that states the allowed range, and the run SHALL stay paused. An unknown run SHALL return not found.

#### Scenario: Capacity out of range
- **WHEN** a client confirms a capacity above the ceiling
- **THEN** the API returns an error with the allowed range

### Requirement: Direct capacity check
The API SHALL run the capacity proposal for a position and flexible-connection setting without starting a workflow, and SHALL return it in under 1 second.

#### Scenario: Pin moved
- **WHEN** a client posts a new position
- **THEN** the API returns a capacity proposal for that position in under 1 second

### Requirement: Clear error when Temporal is unavailable
When Temporal is unreachable, the API SHALL return a service-unavailable response that names `temporal server start-dev`.

#### Scenario: Server down
- **WHEN** the Temporal server is not running and a client starts a run
- **THEN** the API returns a service-unavailable response with that message
