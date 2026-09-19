## 1. F1 link-location-extraction

- [x] 1.1 Team decision, 10 min: `httpx` or Tavily Extract for page fetch; write the choice in `design.md`; verify the chosen client's key is in `.env.example` if one is needed
- [x] 1.2 Write `location/fetch.py` with the URL-keyed cache and `PageUnavailable`; verify a second call for the same URL makes no network request (network off)
- [x] 1.3 Write `location/extract.py` (`ExtractedLocation`, Pydantic AI agent with `gemini_model()`); verify one live call on a saved property page returns an address and postcode
- [x] 1.4 Write `resolve_from_link` with postcode validation, UK check, geocoding, and the artifact (link, model, confidence); verify by printing results for a page with a postcode, one with coordinates only, and one non-UK page (fails clearly)
- [x] 1.5 Wire into `stages/location.py` (postcode given wins; failures become non-retryable with the `--postcode` hint); verify a run with both link and postcode fetches nothing, and a page with no address fails with a message that mentions `--postcode`
- [x] 1.6 Cache 2–3 demo links under `data/fixtures/pages/`; verify `start <demo-link> --yes` resolves each to the expected postcode with the network off
