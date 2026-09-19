## Context

Replaces the link branch of the skeleton's `resolve_location` (`LocationInput → LocationOutput`). The postcode branch (postcodes.io geocoding) belongs to `add-ukpn-capacity-proposal`. Gemini via `llm.gemini_model()` and Pydantic AI are already wired.

## Goals / Non-Goals

**Goals:** a reliable link → postcode for the demo links; honest failure otherwise.

**Non-Goals:** browser automation; scraping at scale.

## Decisions

### Layout

```
src/bessible/location/
  fetch.py      # fetch + cache (httpx)
  extract.py    # Pydantic AI agent
data/fixtures/pages/<sha1(url)>.json     # cached {url, fetched_at, text}
```

### Fetch Client Decision

We choose `httpx` for page fetching over Tavily Extract:
- `httpx` is already an existing project dependency and requires no extra API keys.
- Cached JSON fixtures under `data/fixtures/pages/` ensure tests and demo runs work reliably offline without network dependencies.
- HTML text extraction combined with Gemini structured output handles property listing pages cleanly.
- No new environment variables are required in `.env.example`.

### Interfaces

```python
class ExtractedLocation(BaseModel):          # shallow, for Gemini structured output
    address: str | None
    postcode: str | None
    lat: float | None
    lon: float | None
    country: str | None
    confidence: float

async def fetch_page_text(url: str) -> str                      # cached; raises PageUnavailable
async def extract_location(text: str) -> ExtractedLocation      # Gemini structured output
async def resolve_from_link(url: str, run_id: str) -> LocationOutput
class LocationNotFound(Exception): ...                          # mapped to a non-retryable ApplicationError
```

Page text is trimmed to a fixed length before it goes to the model. The stage wrapper maps `PageUnavailable` and `LocationNotFound` to non-retryable errors, so Temporal does not retry a page that will never have an address. Network errors other than these remain retryable.

**Why structured output with a validator:** the model can return a plausible but wrong postcode. The postcode must geocode, and the extract's country must be the UK, or the stage fails. The artifact records model and confidence.

**Alternative rejected:** regex only. It fails on the many layouts of property pages; the model handles layout and the validator handles correctness.

## Risks / Trade-offs

- [Page blocks bots or needs JavaScript] → Fails clearly with the `--postcode` hint; demo links are cached ahead of time.
- [Wrong postcode from a page listing several addresses] → The prompt asks for the property's own address; confidence is recorded; the CLI shows the postcode before confirmation (already in the skeleton's prompt via the capacity proposal).
- [Model cost or latency] → One call per link, cached page, small text limit.

## Open Questions

- None. `httpx` chosen per task 1.1.
