## Purpose

Presents the finished assessment in the browser with the evidence behind every figure, and says plainly that it is a screening estimate.

## ADDED Requirements

### Requirement: Report sections
The report page SHALL show: the capacity range and binding constraint, the grid connection summary, land and planning risk, the duration comparison, and the financial summary.

#### Scenario: All sections
- **WHEN** a run has completed
- **THEN** the page shows all five sections

### Requirement: Every figure shows its source
Each figure SHALL show its data source and its snapshot or as-of date, and SHALL link to the artifact that supports it.

#### Scenario: Source shown
- **WHEN** the page shows the firm capacity
- **THEN** it also shows the dataset name, the snapshot date, and a link to the artifact

### Requirement: Screening notice
The page SHALL show a notice that the outputs are screening estimates, not advice.

#### Scenario: Notice visible
- **WHEN** the report page loads
- **THEN** the notice is visible without scrolling past the verdict

### Requirement: Same content as the CLI report
The page SHALL render from the same result the CLI report uses, and SHALL NOT compute figures of its own.

#### Scenario: Same figures
- **WHEN** the same run is read through the CLI and the page
- **THEN** every figure is identical
