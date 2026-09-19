## Purpose

Lets the team rebuild the UKPN snapshot safely and makes its age visible, so a stale snapshot is never mistaken for current data.

## ADDED Requirements

### Requirement: Refresh replaces the snapshot atomically
The refresh command SHALL build the new snapshot in a temporary folder and replace the existing one only when every dataset succeeds. A failed refresh SHALL leave the existing snapshot unchanged.

#### Scenario: Successful refresh
- **WHEN** refresh runs and all datasets download
- **THEN** the snapshot folder holds the new data and manifest

#### Scenario: One dataset fails
- **WHEN** refresh runs and one dataset fails to download
- **THEN** the existing snapshot is unchanged and the command exits with an error naming the dataset

### Requirement: Refresh reports what changed
The refresh command SHALL print the number of rows added, removed and changed per dataset.

#### Scenario: Diff summary
- **WHEN** a refresh completes
- **THEN** the output lists added, removed and changed row counts for each dataset

### Requirement: Snapshot age is visible
The report SHALL state the snapshot date and its age in days. The CLI SHALL print a warning when the snapshot is more than 6 months old.

#### Scenario: Old snapshot
- **WHEN** the snapshot was fetched 7 months ago
- **THEN** the CLI prints a warning and the report states the age

#### Scenario: Fresh snapshot
- **WHEN** the snapshot is 2 months old
- **THEN** no warning is printed
