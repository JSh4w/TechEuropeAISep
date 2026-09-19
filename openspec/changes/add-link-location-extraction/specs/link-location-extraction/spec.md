## Purpose

Turns a property link into a UK postcode and map position that the rest of the assessment can use, with evidence for how it was found.

## ADDED Requirements

### Requirement: Location is extracted from the page
Given a property link, the system SHALL fetch the page and extract the address, the postcode, and the coordinates when present, using a model with structured output. It SHALL return the postcode and a position, and an artifact that cites the link and records the model and a confidence.

#### Scenario: Page with a postcode
- **WHEN** the page shows an address with a valid UK postcode
- **THEN** the output has that postcode, a position, and an artifact citing the link

#### Scenario: Page with coordinates only
- **WHEN** the page gives coordinates but no postcode
- **THEN** the output has the position and the nearest postcode from reverse lookup

### Requirement: Extracted postcode is validated
The system SHALL accept an extracted postcode only if it is a valid UK postcode and can be geocoded. Otherwise it SHALL treat the extraction as failed.

#### Scenario: Invalid postcode
- **WHEN** the model returns "XX1 1XX" and geocoding fails
- **THEN** the extraction fails

### Requirement: A given postcode wins
When the request has both a link and a postcode, the system SHALL use the postcode and SHALL NOT fetch the page.

#### Scenario: Both given
- **WHEN** a request has a link and the postcode "SW1A 1AA"
- **THEN** the output uses "SW1A 1AA" and no page is fetched

### Requirement: Failure is clear and not retried
When the page cannot be fetched, has no address, or the address is outside the UK, the system SHALL fail the stage without retrying, with a message that suggests the `--postcode` option.

#### Scenario: No address on page
- **WHEN** the page contains no address
- **THEN** the run fails with a message that mentions `--postcode`

#### Scenario: Non-UK address
- **WHEN** the page shows an address outside the UK
- **THEN** the run fails with a message that says only UK sites are supported

### Requirement: Fetched pages are cached
The system SHALL cache each fetched page by its link and reuse the cache on later runs, so a demo link gives the same result every time.

#### Scenario: Second run
- **WHEN** the same link is used again
- **THEN** no network fetch happens and the same postcode is returned
