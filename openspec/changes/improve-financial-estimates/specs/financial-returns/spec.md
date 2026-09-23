## ADDED Requirements

### Requirement: Cash flow changes year by year
The system SHALL compute each year's cash flow separately over the project life, applying: battery capacity fade at a documented rate per year, an augmentation capital cost in a documented year that restores capacity, a documented revenue decline for both balancing and wholesale revenue, inflation indexing of revenue and operating cost, and a decommissioning cost in the final year.

#### Scenario: Degradation lowers revenue
- **WHEN** fade is 2% per year and no augmentation has happened yet
- **THEN** year 5 revenue before inflation is lower than year 1 revenue

#### Scenario: Augmentation
- **WHEN** augmentation is documented for year 11
- **THEN** year 11 has an augmentation cost and year 12 capacity is back at the documented restored level

### Requirement: Corporation tax with capital allowances
The system SHALL deduct corporation tax at the documented rate on taxable profit, where taxable profit is revenue minus operating cost, interest and capital allowances at documented rates. Tax losses SHALL carry forward and SHALL NOT produce a negative tax payment.

#### Scenario: Early losses
- **WHEN** capital allowances exceed profit in the first years
- **THEN** tax in those years is zero and the losses reduce tax in later years

### Requirement: Low and high bounds per case
The system SHALL return, for each duration case, a low bound and a high bound with capital cost, NPV, IRR and payback years. The low bound SHALL combine the pessimistic end of every range (high cost, low revenue, high rates) and the high bound SHALL combine the optimistic end.

#### Scenario: Bounds bracket the mid case
- **WHEN** a case is computed
- **THEN** its low-bound NPV is at or below the mid NPV and its high-bound NPV is at or above it

### Requirement: Each input is named in an artifact
The system SHALL return an artifact per duration case that names the site-specific inputs used (substation demand, distance, voltage, TNUoS zone, revenue sources and whether they were live or cached).

#### Scenario: Traceable case
- **WHEN** the 4-hour case is produced
- **THEN** its artifact lists the substation, TNUoS zone and each revenue source with its as-of date
