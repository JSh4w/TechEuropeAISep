## ADDED Requirements

### Requirement: Wholesale arbitrage from market prices
The system SHALL compute wholesale arbitrage revenue per MW per year for 2-hour, 4-hour and 8-hour batteries from the last 12 months of published GB market index prices, multiplied by a documented capture factor below 100%, because perfect foresight overstates what a real battery earns. For each day the battery SHALL charge in the cheapest periods and discharge in the most expensive periods that fit its duration, with at most one cycle per day, net of the documented round-trip efficiency.

#### Scenario: Longer duration earns more per MW
- **WHEN** arbitrage is computed from the same 12 months of prices
- **THEN** the 8-hour value is at or above the 4-hour value, which is at or above the 2-hour value

#### Scenario: Losses applied
- **WHEN** round-trip efficiency is 85%
- **THEN** for each MWh sold, the battery buys 1 / 0.85 MWh to charge, and the day's revenue is the sale value minus that purchase cost

#### Scenario: Source stated
- **WHEN** the live price source succeeds
- **THEN** the artifact names the dataset, the date range, and says the figure is live, not cached

### Requirement: Capacity Market from the latest auction
The system SHALL use the clearing price of the latest T-4 Capacity Market auction and the de-rating factors published for that auction. These figures SHALL be a documented assumption that names the auction and its date, and the artifact SHALL say the figure is from a published auction result, not a live feed.

#### Scenario: Auction figures used
- **WHEN** the market stage computes Capacity Market revenue for 4 hours
- **THEN** it equals the recorded clearing price times the recorded 4-hour de-rating factor, and the artifact names the auction

#### Scenario: Unchecked figures are flagged
- **WHEN** the recorded auction figures are still marked placeholder
- **THEN** the artifact says the figure is a placeholder
