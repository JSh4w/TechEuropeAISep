## Purpose

Provides the UKPN capacity data as a local, validated, read-only snapshot with provenance, so the capacity proposal runs offline and every figure can be traced to a dataset and a date.

## ADDED Requirements

### Requirement: Ingest builds a snapshot from UKPN datasets
The system SHALL provide an ingest command that fetches these UKPN datasets with an authenticated API key and writes them to local files: the LTDS Capacity Heatmap, Primary Substation Distribution Areas, the Embedded Capacity Register, Grid Supply Points Overview, and GSP Project Status. The command SHALL rebuild the whole snapshot each time and SHALL NOT edit an existing snapshot in place.

#### Scenario: Successful ingest
- **WHEN** the ingest command runs with a valid API key
- **THEN** the snapshot folder contains one file per dataset and a manifest

#### Scenario: Missing key
- **WHEN** the ingest command runs without an API key
- **THEN** it fails with a message naming the missing setting and leaves any existing snapshot unchanged

### Requirement: Manifest records provenance
The snapshot SHALL include a manifest with the fetch timestamp, the source dataset ids, and the row count per dataset. Every figure the system reports from the snapshot SHALL be attributable to a dataset id and the snapshot date.

#### Scenario: Manifest content
- **WHEN** an ingest completes
- **THEN** the manifest lists all five datasets with their row counts and the fetch timestamp

### Requirement: Snapshot is validated on load
The system SHALL validate every snapshot row against its typed model when loading. If a row fails, the system SHALL fail with the dataset name and row identifier. Rows with a blank connection voltage SHALL get the voltage parsed from the substation name. A row whose voltage cannot be determined SHALL fail validation.

#### Scenario: Blank voltage
- **WHEN** a substation has a blank voltage field and the name "Example Primary 11kV"
- **THEN** it loads with a connection voltage of 11 kV

#### Scenario: Malformed row
- **WHEN** a row has a non-numeric capacity
- **THEN** loading fails and the message names the dataset and the row

### Requirement: Geometry is simplified for point-in-polygon use
The system SHALL store distribution-area polygons as GeoJSON simplified to about 100 vertices per polygon. The snapshot SHALL be small enough to commit to the repository.

#### Scenario: Simplified geometry
- **WHEN** an ingest completes
- **THEN** no distribution-area polygon has more than about 150 vertices and the snapshot folder is under 10 MB

### Requirement: Runs use only local data
The system SHALL NOT call UKPN services when loading the snapshot or proposing capacity.

#### Scenario: Offline proposal
- **WHEN** the network is unavailable and a capacity proposal is requested for a known position
- **THEN** it completes from the local snapshot
