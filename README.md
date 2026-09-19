# Bessible — BESS Site Assessment Agent

Bessible assesses real estate properties for Battery Energy Storage Systems (BESS) feasibility and suitability in the UK. Given a property link or postcode, it coordinates grid connection analysis, title boundaries, planning policy, market revenue, local sentiment, and financial returns with full explainability and durable human-in-the-loop orchestration.

---

## Running the Backend

### 1. Prerequisites & Environment Check

Ensure your `.env` contains your API keys (`GOOGLE_API_KEY`, `PYDANTIC_AI_GATEWAY_API_KEY` are required):

```bash
# Check keys, Temporal reachability, and Modal login
uv run python scripts/check_env.py
```

### 2. Start Temporal Server

The backend uses [Temporal](https://temporal.io) to orchestrate durable workflow execution:

```bash
temporal server start-dev
```
* Temporal Web UI is accessible at **http://localhost:8233**.

### 3. Start the Backend Worker

In a separate terminal, launch the Bessible worker listening on task queue `bessible`:

```bash
uv run python -m bessible.worker
```

> **Demo Tip (Activity Retries):** To demonstrate live retry recovery on transient failures, launch the worker with:
> ```bash
> BESSIBLE_DEMO_FAIL_ONCE=1 uv run python -m bessible.worker
> ```

### 4. Start the FastAPI HTTP Server

To serve the web UI, SSE progress traces, and fast capacity checks:

```bash
uv run uvicorn bessible.api.app:app --host 0.0.0.0 --port 8000
```

---

## CLI Usage

The backend CLI (`bessible.cli`) allows you to start assessments, confirm site parameters, and inspect results.

### Starting an Assessment

```bash
# Attached interactive mode (guides you through progress & asks for confirmation)
uv run python -m bessible.cli start --postcode "OX14 4TE"

# Start with property link and target parameters
uv run python -m bessible.cli start "https://example.com/property" --battery-mw 20 --budget-gbp 10000000

# Enable flexible connection (allows connecting above firm headroom up to ceiling)
uv run python -m bessible.cli start --postcode "OX14 4TE" --flexible

# Auto-confirm defaults without interactive prompting
uv run python -m bessible.cli start --postcode "OX14 4TE" --yes

# Detached mode (starts run in background and prints run ID)
uv run python -m bessible.cli start --postcode "OX14 4TE" --detach
```

### Confirming a Paused Run (Human-in-the-Loop)

When a run reaches the `awaiting_confirmation` checkpoint, use `confirm`:

```bash
# Confirm using recommended capacity
uv run python -m bessible.cli confirm <run-id>

# Confirm with custom capacity within approved range
uv run python -m bessible.cli confirm <run-id> --capacity-mw 15.0

# Reject site proposal
uv run python -m bessible.cli confirm <run-id> --reject
```

### Viewing Run Results & Reports

```bash
# View active progress or final report, duration comparison table, and artifact path
uv run python -m bessible.cli result <run-id>
```

All generated evidence artifacts, GeoJSON boundaries, and Markdown reports are saved to:
`out/<run-id>/report.md`

---

## Standalone Diagnostics & Data Tools

### Site Data Report

Generate a consolidated raw environmental and grid data report for any location:

```bash
uv run python scripts/site_report.py --postcode "RH3 7EZ"
```

### Location Pipeline Collation

Test coordinate geocoding, boundary retrieval, flood zones, and designations:

```bash
uv run python -m bessible.location 51.2471 -0.2668
```

### Automated Tests & Linting

```bash
# Run all backend unit and integration tests
uv run pytest

# Check code formatting and linting
uv run ruff check src/ tests/
```

---

## Architecture & How to Replace a Stage

The pipeline runs as a durable Temporal workflow (`AssessmentWorkflow`):

1. **Sequential Front**: `resolve_location` &rarr; `propose_capacity` (with early stop for out-of-area/non-viable sites) &rarr; `find_title_boundaries`.
2. **Human-in-the-Loop**: Pauses with `status="awaiting_confirmation"`. Validates user decision via `decide_site` update.
3. **Parallel Group 1**: `grid_connection`, `site_land`, `market_revenue`, `local_sentiment`.
4. **Parallel Group 2**: `financial_model`, `regulatory_planning`.
5. **Synthesis**: Compiles Markdown report and verifies that all claims cite evidence artifact IDs.

Each assessment stage is an independent `async` function in `src/bessible/stages/<stage>.py`. You can swap or customize any stage implementation without modifying workflow or worker logic.

### Stage Signatures

```python
from bessible.models import (
    CapacityInput, CapacityOutput,
    FinancialInput, FinancialOutput,
    GridOutput, LocationInput, LocationOutput,
    MarketOutput, NodeInput, PlanningInput,
    PlanningOutput, ReportOutput, SentimentOutput,
    SiteLandOutput, SynthesisInput, TitleInput, TitleOutput,
)

# 1. Location (src/bessible/stages/location.py)
async def resolve_location(inp: LocationInput) -> LocationOutput: ...

# 2. Grid Capacity (src/bessible/stages/capacity.py)
async def propose_capacity(inp: CapacityInput) -> CapacityOutput: ...

# 3. Title Boundaries (src/bessible/stages/title.py)
async def find_title_boundaries(inp: TitleInput) -> TitleOutput: ...

# 4. Grid Connection (src/bessible/stages/grid.py)
async def grid_connection(inp: NodeInput) -> GridOutput: ...

# 5. Site & Land Constraints (src/bessible/stages/site_land.py)
async def site_land(inp: NodeInput) -> SiteLandOutput: ...

# 6. Market Revenue Projections (src/bessible/stages/market.py)
async def market_revenue(inp: NodeInput) -> MarketOutput: ...

# 7. Local Community Sentiment (src/bessible/stages/sentiment.py)
async def local_sentiment(inp: NodeInput) -> SentimentOutput: ...

# 8. Financial Model (src/bessible/stages/financial.py)
async def financial_model(inp: FinancialInput) -> FinancialOutput: ...

# 9. Regulatory & Planning (src/bessible/stages/planning.py)
async def regulatory_planning(inp: PlanningInput) -> PlanningOutput: ...

# 10. Synthesis & Report (src/bessible/stages/synthesis.py)
async def synthesise(inp: SynthesisInput) -> ReportOutput: ...
```

---

## Setup Script Reference

```bash
./scripts/setup.sh    # Installs uv, Temporal CLI, Node, Python deps, creates .env, logs in to Modal
./scripts/dev.sh      # Starts Temporal + worker + web UI in one command
```
