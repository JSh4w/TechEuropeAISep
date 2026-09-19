## Why

Bessible has three people building stages in parallel, and nothing yet to plug them into. A runnable Temporal pipeline with placeholder stages, typed models and a CLI lets teammates replace one stage at a time while the whole demo keeps working end-to-end.

**Owner:** Josh.

## What Changes

- Add the shared Pydantic models: request (property link or postcode), one input/output pair per stage, `ConfirmedSite`, and `Artifact` (claim, source URL or file, image, confidence, model used).
- Add a Temporal workflow with this shape:
  1. `resolve_location` (link → postcode + lat/long), `propose_capacity`, `find_title_boundaries`, in order.
  2. **Human confirmation** of position and capacity.
  3. In parallel: `grid_connection`, `site_land`, `market_revenue`.
  4. In parallel: `financial_model`, `regulatory_planning`.
  5. `synthesis` builds the report.
- Add one placeholder activity per stage, each a thin wrapper around a plain async function that teammates replace. Placeholders return realistic fixed `Artifact`s.
- Confirmation is a Temporal update the CLI sends; it carries the confirmed position and capacity and is rejected if the capacity is out of range.
- Add a worker and a CLI (`start`, `confirm`, `result`) that prints the report and artifact folder.
- Add the `financial_model` contract: 2 h, 4 h and 8 h cases on every run.

## Capabilities

### New Capabilities

- `assessment-models`: Pydantic models for request, stage input/output, confirmed site, and `Artifact`.
- `assessment-workflow`: Temporal workflow, placeholder stages, parallel fan-out, retries, and the confirmation update.
- `assessment-cli`: CLI to start a run, confirm the site, and show the report and artifacts.

### Modified Capabilities

None. `openspec/specs/` is empty.

## Impact

- New code in `src/bessible/` (`models.py`, `stages/`, `activities.py`, `workflow.py`, `worker.py`, `cli.py`). `config.py` and `llm.py` are reused.
- New `out/<run-id>/` folder for artifact files (gitignored).
- Runs on the local Temporal dev server. No new dependencies.
- Follow-on change `add-ukpn-capacity-proposal` fills `propose_capacity` (and the capacity part of `grid_connection`) with real logic.

## Non-goals

- Real stage logic. Each piece is its own change:
  `add-ukpn-capacity-proposal`, `add-grid-connection-context`, `add-link-location-extraction`,
  `add-market-revenue`, `add-financial-model`, `add-regulatory-planning`,
  `add-footprint-sizing`, `add-grid-level-sites`.
- Web UI, FastAPI, SSE trace, map: `add-web-ui`. The CLI is the interface here.
- Deployment, auth, multi-user support.
