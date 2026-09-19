# TechEuropeAISep
Repo for AI hackathon for Tech {Europe}

50% on technical execution 
30% presentation??
20% does it actually solvve a problem


Problem statement  
Build an agent with >=2 tech partners from this event 


deepmind llama : do you save cache between those multiple models/ threads? Consumes a bunch of tokens

## Setup (macOS or Linux)

```bash
./scripts/setup.sh    # installs uv + Temporal CLI (via Homebrew on Mac), Python deps, creates .env, logs in to Modal
```

1. Fill in `.env` with the keys (get them from Josh privately, never commit `.env`). `GOOGLE_API_KEY` and `PYDANTIC_AI_GATEWAY_API_KEY` are required.
2. Accept the invite to Josh's Modal workspace, then `uv run modal profile activate <workspace>` if you're in more than one.
3. Start Temporal in its own terminal: `temporal server start-dev` (UI at http://localhost:8233).
4. Check everything: `uv run python scripts/check_env.py` (add `--live` to test Gemini and the Modal model)
5. Map prototype (base for the final build): see `sandbox/map_session/web/README.md`.

Run Python with `uv run ...` (or `source .venv/bin/activate`). Add packages with `uv add <pkg>`, not pip.
For OpenSpec's `/opsx` commands: `npm install -g @fission-ai/openspec@latest`.

## Workflow

1. Everyone writes a 1-page plan in `docs/plans/<name>.md` (copy `docs/plans/TEMPLATE.md`).
2. Together: `/opsx:explore` in Claude Code to merge the plans, then `/opsx:propose <change>` once per person's workstream.
3. Each person builds their own change with `/opsx:apply <change>`. Pull often, only edit files you own.

## How to replace a stage

Each assessment stage is an independent, plain `async` function in `src/bessible/stages/`. To implement or customize a stage, you only need to edit your stage's module in `src/bessible/stages/<stage>.py` without touching workflow or worker code.

Each stage receives a typed input model and returns a typed output model carrying `Artifact`s with supporting evidence (source URLs or relative files saved to `out/<run_id>/`).

### Stage function signatures

```python
from bessible.models import (
    LocationInput, LocationOutput,
    CapacityInput, CapacityOutput,
    TitleInput, TitleOutput,
    NodeInput, GridOutput, SiteLandOutput, MarketOutput,
    FinancialInput, FinancialOutput,
    PlanningInput, PlanningOutput,
    SynthesisInput, ReportOutput,
)

# 1. Location Resolution (src/bessible/stages/location.py)
async def resolve_location(inp: LocationInput) -> LocationOutput: ...

# 2. Grid Capacity Proposal (src/bessible/stages/capacity.py)
async def propose_capacity(inp: CapacityInput) -> CapacityOutput: ...

# 3. Title Boundaries (src/bessible/stages/title.py)
async def find_title_boundaries(inp: TitleInput) -> TitleOutput: ...

# 4. Grid Connection (src/bessible/stages/grid.py)
async def grid_connection(inp: NodeInput) -> GridOutput: ...

# 5. Site & Land Constraints (src/bessible/stages/site_land.py)
async def site_land(inp: NodeInput) -> SiteLandOutput: ...

# 6. Market Revenue Projections (src/bessible/stages/market.py)
async def market_revenue(inp: NodeInput) -> MarketOutput: ...

# 7. Financial Model (src/bessible/stages/financial.py)
async def financial_model(inp: FinancialInput) -> FinancialOutput: ...

# 8. Regulatory & Planning (src/bessible/stages/planning.py)
async def regulatory_planning(inp: PlanningInput) -> PlanningOutput: ...

# 9. Synthesis & Report (src/bessible/stages/synthesis.py)
async def synthesise(inp: SynthesisInput) -> ReportOutput: ...
```

### Running the pipeline

1. **Start Temporal dev server:**
   ```bash
   temporal server start-dev
   ```
2. **Start the worker in its own terminal:**
   ```bash
   uv run python -m bessible.worker
   ```
3. **Run an assessment from the CLI:**
   ```bash
   # Attached interactive mode
   uv run python -m bessible.cli start --postcode "OX14 4TE"

   # Auto-confirm defaults
   uv run python -m bessible.cli start --postcode "OX14 4TE" --yes

   # Detached mode
   uv run python -m bessible.cli start --postcode "OX14 4TE" --detach
   uv run python -m bessible.cli confirm <run-id> [--capacity-mw 12.0]
   uv run python -m bessible.cli result <run-id>
   ```
