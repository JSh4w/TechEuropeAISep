## Context

See proposal.md for motivation. Existing code: `config.py` (`settings` incl. `temporal_address`, `temporal_namespace`) and `llm.py` (model factories). `temporalio` and `pydantic-ai-slim[temporal]` are installed. Runs locally against `temporal server start-dev`. Workflow code must be deterministic (CLAUDE.md), so all I/O and file writes happen in activities.

The workflow shape comes from the team's UKPN capacity proposal (fan-out of agent nodes, then synthesis). It maps onto CLAUDE.md's pipeline like this:

| CLAUDE.md step | Stages here |
|---|---|
| Grid connection check | `resolve_location`, `propose_capacity` |
| Title boundaries | `find_title_boundaries` |
| Human in the loop | `decide_site` update |
| Feasibility engine | `grid_connection`, `site_land`, `regulatory_planning` |
| Suitability engine | `market_revenue`, `financial_model` |
| Report | `synthesis` |

## Goals / Non-Goals

**Goals:**
- Teammates build against fixed function signatures and models, with no workflow knowledge.
- One `uv run` command starts the worker; one starts a full demo run.

**Non-Goals:**
- Streaming partial results (SSE), workflow versioning, or multi-tenant task queues.
- Any real stage logic. Each feature has its own change (listed in proposal.md Non-goals).

## Decisions

### Layout

```
src/bessible/
  models.py        # all Pydantic models (below)
  stages/          # one module per stage: plain async functions, teammates own these
    location.py capacity.py title.py grid.py site_land.py market.py
    financial.py planning.py synthesis.py
  activities.py    # thin @activity.defn wrappers, one per stage (Josh only)
  workflow.py      # AssessmentWorkflow (Josh only)
  worker.py        # `uv run python -m bessible.worker`
  cli.py           # `uv run python -m bessible.cli ...`
```

**Why plain functions plus wrappers:** matches the CLAUDE.md decision. A teammate edits one file in `stages/`; the wrapper's signature never changes. A Modal function can be called from inside a stage function.

**`propose_capacity` is also a plain function** with no Temporal imports, so a later map UI can call it directly for sub-second re-checks without going through the workflow.

### Models (`models.py`)

```python
Stage = Literal["location","capacity","title","grid","site_land","market","financial","planning","synthesis"]
Verdict = Literal["go", "maybe", "no_go"]

class AssessmentRequest(BaseModel):
    property_url: HttpUrl | None = None
    postcode: str | None = None          # UK postcode
    battery_mw: float | None = None
    budget_gbp: float | None = None
    flexible_connection: bool = False
    # validator: property_url or postcode is required

class Position(BaseModel):
    lat: float
    lon: float

class Artifact(BaseModel):
    id: str                      # "<stage>-<n>", unique per run
    stage: Stage
    claim: str
    source_url: HttpUrl | None = None
    file_path: str | None = None   # relative to out/<run_id>/
    image_path: str | None = None  # relative to out/<run_id>/
    confidence: float = Field(ge=0, le=1)
    model_used: str              # e.g. "gemini-3.7-flash", "modal:gemma-4-31B-it", "ukpn-snapshot", "dummy"
    # validator: at least one of source_url / file_path / image_path

class StageInput(BaseModel):
    run_id: str
    request: AssessmentRequest

# --- before confirmation
class LocationInput(StageInput): ...
class LocationOutput(BaseModel):
    postcode: str
    position: Position
    artifacts: list[Artifact]

class CapacityInput(StageInput):
    location: LocationOutput
class CapacityOutput(BaseModel):
    viable: bool
    message: str | None                     # required when not viable
    out_of_area: bool                       # implies viable == False
    substation: str | None
    connection_voltage_kv: float | None
    firm_mw: float
    ceiling_mw: float                       # >= firm_mw
    recommended_mw: float
    binding_direction: Literal["import", "export"] | None
    binding_season: Literal["winter", "summer"] | None
    distance_km: float | None
    artifacts: list[Artifact]
    # Follow-on change add-ukpn-capacity-proposal may ADD optional fields.

class TitleInput(StageInput):
    location: LocationOutput
    capacity: CapacityOutput
class TitleOutput(BaseModel):
    title_number: str
    boundary_geojson: dict[str, Any]
    area_m2: float
    artifacts: list[Artifact]

class SiteDecision(BaseModel):          # sent by the CLI
    confirmed: bool
    position: Position | None = None        # None = proposal default
    capacity_mw: float | None = None        # None = capacity.recommended_mw

class ConfirmedSite(BaseModel):         # built by the workflow, not by a stage
    position: Position
    capacity_mw: float
    boundary: TitleOutput
    footprint_geojson: dict[str, Any] | None = None   # None until a map step exists
    # validator (given capacity + request): capacity_mw <= ceiling_mw; <= firm_mw unless flexible

# --- after confirmation (all inherit StageInput and carry `site` and `capacity`)
class NodeInput(StageInput):
    site: ConfirmedSite
    capacity: CapacityOutput

class GridOutput(BaseModel):
    gate2_queue_position: int | None
    indicative_connection_months: int | None
    artifacts: list[Artifact]
class SiteLandOutput(BaseModel):
    land_use: str
    constraints: list[str]
    artifacts: list[Artifact]
class MarketOutput(BaseModel):
    revenue_gbp_per_mw_year: float
    streams: dict[str, float]
    artifacts: list[Artifact]

class FinancialInput(NodeInput):  grid: GridOutput; market: MarketOutput
class DurationCase(BaseModel):
    duration_h: Literal[2, 4, 8]
    capex_gbp: float
    npv_gbp: float
    irr: float | None
class FinancialOutput(BaseModel):
    cases: list[DurationCase]           # exactly durations 2, 4, 8
    artifacts: list[Artifact]

class PlanningInput(NodeInput):  grid: GridOutput; site_land: SiteLandOutput
class PlanningOutput(BaseModel):
    consenting_route: str
    risks: list[str]
    artifacts: list[Artifact]

class Finding(BaseModel):
    text: str
    artifact_ids: list[str] = Field(min_length=1)
class SynthesisInput(NodeInput):
    grid: GridOutput; site_land: SiteLandOutput; market: MarketOutput
    financial: FinancialOutput; planning: PlanningOutput
    artifacts: list[Artifact]           # every artifact so far
class ReportOutput(BaseModel):
    verdict: Verdict
    findings: list[Finding]
    report_path: str                    # relative to out/<run_id>/
    artifacts: list[Artifact]

class RunStatus(BaseModel):
    status: Literal["running", "awaiting_confirmation", "completed", "rejected", "out_of_area", "not_viable", "failed"]
    stages: list[Stage]                 # stages running now
    capacity: CapacityOutput | None     # set once known
    boundary: TitleOutput | None        # set while awaiting_confirmation
class AssessmentResult(BaseModel):
    status: Literal["completed", "rejected", "out_of_area", "not_viable"]
    message: str | None                 # set for out_of_area / not_viable
    report: ReportOutput | None
    financial: FinancialOutput | None
    artifacts: list[Artifact]
    run_dir: str
```

Stage function contract (what teammates implement). Stages write any artifact file or image into `out/<inp.run_id>/` and return the relative path.

```python
async def resolve_location(inp: LocationInput) -> LocationOutput
async def propose_capacity(inp: CapacityInput) -> CapacityOutput
async def find_title_boundaries(inp: TitleInput) -> TitleOutput
async def grid_connection(inp: NodeInput) -> GridOutput
async def site_land(inp: NodeInput) -> SiteLandOutput
async def market_revenue(inp: NodeInput) -> MarketOutput
async def financial_model(inp: FinancialInput) -> FinancialOutput
async def regulatory_planning(inp: PlanningInput) -> PlanningOutput
async def synthesise(inp: SynthesisInput) -> ReportOutput
```

### Workflow (`workflow.py`)

- `AssessmentWorkflow.run(request: AssessmentRequest) -> AssessmentResult`. Run id = workflow id (`bessible-<uuid>` chosen by the CLI, so it can print the id before the run starts).
- Task queue: `bessible`.
- Each stage is one `workflow.execute_activity` with `start_to_close_timeout=60s` (agent nodes: 180s) and `RetryPolicy(maximum_attempts=3, non_retryable_error_types=["ValidationError"])`. Activity wrappers convert Pydantic `ValidationError` into a non-retryable `ApplicationError`.
- Parallel groups use `asyncio.gather` over `execute_activity` calls. Temporal's deterministic event loop makes this safe in workflow code.
- If `capacity.out_of_area`, return `AssessmentResult(status="out_of_area", message=...)` before the pause; else if not `capacity.viable`, return `status="not_viable"`.
- Human-in-the-loop: update `decide_site(SiteDecision) -> None`, with a validator that rejects a capacity outside `(0, ceiling]` (or `(0, firm]` without flexible connection) so the CLI gets an immediate error and the run stays paused. The workflow waits with `workflow.wait_condition`. No timeout, so the demo can pause as long as needed. The workflow then builds `ConfirmedSite`.
- Query `status() -> RunStatus`. The workflow sets `_stages` and `_status` around each step, and `boundary` while it waits.
- A rejected decision returns `AssessmentResult(status="rejected")`. It is a normal result, not a failure.

**Why an update, not a signal:** the validator gives the CLI an error for an out-of-range capacity without failing the workflow task. A signal cannot reply.

**Alternative rejected:** child workflow per stage. It adds ceremony and no benefit at this size.

### Client and worker

- Client: `Client.connect(settings.temporal_address, namespace=settings.temporal_namespace, plugins=[PydanticAIPlugin()])`. The plugin installs the Pydantic data converter and lets Pydantic AI agents run in activities/workflows later with no client change.
- Worker registers `AssessmentWorkflow` and the nine activities on task queue `bessible`.

### Agent nodes (guidance for teammates, not built here)

`grid_connection`, `site_land`, `market_revenue`, `financial_model`, `regulatory_planning` and `synthesise` may use Pydantic AI agents with `gemini_model()` and structured output from their output model. Keep those models shallow: Gemini rejects deeply nested schemas. Financial figures (CAPEX, OPEX, NPV, IRR) are computed in plain code; the model only narrates. Record the model in `Artifact.model_used`.

### Placeholder stages

Each `stages/*.py` ships with a dummy that returns fixed, believable data (a postcode, a viable 12 MW firm / 20 MW ceiling capacity limited by import, a Land Registry-style title number, a GeoJSON polygon, three duration cases, a verdict of `go`) and writes one small file, so the artifact-folder demo works from day one. `model_used="dummy"`. The `propose_capacity` placeholder returns `out_of_area=True` for the postcode `ZZ99 9ZZ` and `viable=False` for `ZZ99 8ZZ`, so both early-stop paths are testable. `grid_connection` fails once on the first attempt when env var `BESSIBLE_DEMO_FAIL_ONCE=1`, to show retries live.

### CLI (`cli.py`, argparse)

`start [url] [--postcode P] [--battery-mw N] [--budget-gbp N] [--flexible] [--detach] [--yes]`, `confirm <run-id> [--capacity-mw N] [--reject]`, `result <run-id>`. Attached `start` polls `status()` every 0.5 s and prints a line per stage change. On `awaiting_confirmation` it prints the capacity proposal and boundary, then asks y/n and a capacity (enter = recommended); an update error reprints the allowed range and asks again. Plain text output; no extra dependency.

**Why argparse:** no new dependency; three commands do not need Typer.

### Report

`stages/synthesis.py` builds Markdown from `SynthesisInput.artifacts` and typed node outputs. Each finding is generated from a single artifact's claim and cites its id. The report shows the capacity range, binding constraint, duration table and verdict. Written to `out/<run_id>/report.md`.

## Risks / Trade-offs

- [Teammates change a shared model and break others] → Models change only by adding optional fields; changes announced in the team chat. Josh owns `models.py`.
- [Temporal sandbox rejects an import in workflow code] → `workflow.py` imports models via `workflow.unsafe.imports_passed_through()` and never imports `stages/`.
- [Non-JSON types such as `HttpUrl` fail in payloads] → The Pydantic converter handles them; check once by running a demo with a URL and a GeoJSON boundary.
- [Indefinite wait for confirmation leaves a stuck run] → Acceptable for the demo; `temporal workflow terminate` cleans up.
- [A parallel node fails and hides the others' work] → The run fails; completed activities stay in Temporal history for debugging.

## Assumptions

- One change covers Josh's whole framework. Stage work (e.g. `add-ukpn-capacity-proposal`) is separate.
- Rejecting the site ends the run. It does not loop back to pick another boundary.
- Budget is in GBP and battery size in MW (UK site).
- `ConfirmedSite.footprint_geojson` stays empty until a map step exists.
- Gemini model: stages use `settings.gemini_model` (currently `gemini-3.7-flash`). The team's UKPN proposal names `gemini-3.8-flash`; changing the default is a one-line `config.py` edit and is not part of this change.
