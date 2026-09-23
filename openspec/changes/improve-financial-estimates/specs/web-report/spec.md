## ADDED Requirements

### Requirement: Financial figures come only from the run result
The report page and its exported document SHALL show capital cost, NPV and IRR only from the run's financial result. When the result has no financial output, they SHALL say the financial model did not run, and SHALL NOT show placeholder figures. A case whose IRR is unset SHALL be shown as "No payback".

#### Scenario: Two sites
- **WHEN** two completed runs have different financial results
- **THEN** the page shows different figures for each

#### Scenario: No financial output
- **WHEN** a run result has no financial output
- **THEN** the financial section says the model did not run and shows no numbers

### Requirement: Ranges are shown
The report page SHALL show, for each duration case, the low, mid and high NPV and IRR, and the discount rate and project life used.

#### Scenario: Range visible
- **WHEN** a case has low and high bounds
- **THEN** the page shows the mid figure with the low-to-high range beside it
