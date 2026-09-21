## Why

Feasibility (Jack) says whether a battery *can* go on the confirmed site. The suitability engine says whether it *should*: what local people think of it, and whether it pays back. This is the agentic part of the demo and where both partners are visible: Gemini researches and reasons, and Modal classifies at scale.

**Owner:** Josh.

## What Changes

Runs after the human confirms the site, inside the skeleton's workflow. Four stages:

- **local-sentiment:** a Gemini research agent uses Google Search to find local news and planning coverage for the site's area. Each paragraph is labelled for stance and concern by the typed classifier on Modal. Plain code rolls the labels into an opposition index and the top concerns. Every paragraph is an artifact with its URL.
- **market-revenue (simplified):** revenue per MW per year for 2, 4 and 8 hours from a committed, sourced assumptions file. No live feeds.
- **financial-analysis:** deterministic CAPEX, OPEX, financing, NPV, IRR, payback and a low/mid/high range for 2, 4 and 8 hours, plus a budget check. A Gemini analyst agent can only call these functions as tools, picks the recommended duration, and explains why. It never writes a figure itself.
- **suitability-verdict:** rules turn the figures and the opposition index into go / maybe / no-go. Gemini writes the findings. Every finding cites artifact ids, and a guard rejects any number that is not in the computed results.
- Agents run within their respective stage activities (`local_sentiment`, `financial_model`), each managed as a durable Temporal activity with retries and timeouts.

## Capabilities

### New Capabilities

- `local-sentiment`: news research, per-paragraph classification, opposition index.
- `financial-analysis`: assumptions, per-duration returns, budget check, analyst agent.
- `suitability-verdict`: rule-based verdict, cited findings, number guard.

### Modified Capabilities

None. `openspec/specs/` is empty. Skeleton additions are listed under Impact.

## Impact

- New `src/bessible/suitability/` package and `data/assumptions/finance.json`, `data/fixtures/news/`.
- Replaces the skeleton placeholders for `market_revenue`, `financial_model` and `synthesise`. Adds one stage, `local_sentiment`, to the skeleton's post-confirmation parallel group. Output models gain optional fields only.
- Uses `bessible.llm.gemini_model()` (gemini-3.8-flash) and `bessible.classifier.classify()` (Modal app `bessible-classifier`). No new dependencies.
- For the hackathon, supersedes `add-financial-model` and `add-market-revenue`, which stay as post-hackathon reference.

## Non-goals

- Live market data, dispatch optimisation, or the 8,760-hour curtailment model.
- Scraping pages that need JavaScript, or paywalled news.
- Social media sentiment.
- Gemma through the Pydantic AI Gateway (optional later, for the gateway prize).
