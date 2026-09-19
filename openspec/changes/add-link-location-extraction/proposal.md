## Why

The product's input is a link to a property, but the capacity proposal needs a postcode and coordinates. The skeleton's `resolve_location` returns a fixed postcode for links. Without a real extraction step, the headline flow ("give it a link") does not work.

**Owner:** TBD. Nobody owns this today.

## What Changes

One feature.

- **F1 link-location-extraction:** fetch the property page, extract the address, postcode and coordinates if present using Gemini structured output through Pydantic AI, geocode the postcode, and return a `LocationOutput` with an artifact that cites the link.
- A postcode given on the command line wins over the link.
- Failure is clear: if the page cannot be read or has no UK address, the run fails with a message that suggests `--postcode`.
- Fetched pages are cached by URL so demo links behave the same every time.

## Capabilities

### New Capabilities

- `link-location-extraction`: property link to postcode and position, with caching and clear failure.

### Modified Capabilities

None.

## Impact

- New `src/bessible/location/` package; replaces the link branch of `stages/location.py`.
- Uses Gemini (Google DeepMind) and Pydantic AI. Uses `geocode_postcode` from `add-ukpn-capacity-proposal` for the postcode step; until that lands, the same call can be stubbed.
- New `data/fixtures/pages/` for cached pages.

## Non-goals

- JavaScript-rendered pages or browser automation.
- More than one property per link.
- Non-UK addresses.
- Reading the property's boundary or land use (other features).

## Open Questions

- Plain `httpx` fetch or Tavily Extract (an event partner)? Tavily may handle more pages and would add a partner to the demo. Decide at task 1.1.
