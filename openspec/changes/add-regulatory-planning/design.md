## Context

Replaces the skeleton's `regulatory_planning` placeholder (`PlanningInput → PlanningOutput`). `PlanningInput` carries `site`, `capacity`, `grid` and `site_land`, so F1 can use the land constraints and F2 can use `capacity.tia_threshold_mw` (added by `add-ukpn-capacity-proposal`).

## Goals / Non-Goals

**Goals:** three independently testable features; F1 and F2 need no model call.

**Non-Goals:** outcome prediction; other UK nations.

## Decisions

### Layout

```
src/bessible/planning/
  route.py       # F1
  tia.py         # F2
  evidence.py    # F3 (REPD lookup + Pydantic AI agent)
  policy.json    # fixed policy set with sources
```

### Interfaces

```python
# F1
def consenting_route(lpa: LpaLookup | None, mw: float) -> RouteStatement
async def lookup_lpa(pos: Position) -> LpaLookup | None      # postcodes.io admin_district + country, cached fixtures

# F2
def tia_statement(threshold_mw: Literal[1, 5] | None, capacity_mw: float, snapshot_date: date) -> TiaStatement

# F3
class NearbyProject(BaseModel): id: str; name: str; mw: float; status: str; status_date: date; distance_km: float
def nearby_batteries(pos: Position, snap: Snapshot, radius_km: float = 5) -> list[NearbyProject]
class CitedStatement(BaseModel): text: str; cites: list[str] = Field(min_length=1)   # shallow for Gemini
class PlanningSummary(BaseModel): statements: list[CitedStatement]
async def summarise(projects: list[NearbyProject], policy: list[PolicyItem]) -> PlanningSummary
```

`PlanningOutput` already has `consenting_route` and `risks`. F2 and F3 add optional `tia: TiaStatement | None`, `nearby: list[NearbyProject] = []`.

### REPD

The source proposal suggests the DESNZ Renewable Energy Planning Database plus a small fixed policy set, and leaves it undecided. This design adopts it, because it is structured data, needs no retrieval, and the fixed set fits in a prompt. Ingest is a new dataset in `ukpn/ingest.py`'s style (`planning/ingest_repd.py`), stored as JSON in `data/repd/`.

### Model use

F3 uses `gemini_model()` through a Pydantic AI agent with `output_type=PlanningSummary`. The schema is shallow, as Gemini rejects deep nesting. A post-check rejects any statement whose `cites` ids are not in the supplied records or policy. Call the agent directly from within the `regulatory_planning` activity.

## Risks / Trade-offs

- [REPD lacks planning decisions for some projects] → Show status as published; do not infer.
- [Model invents a citation] → The post-check compares cited ids to the supplied ids.
- [LPA lookup wrong near boundaries] → Named in the artifact as looked up from the postcode district.

## Open Questions

- Confirm the REPD choice with the team before starting F3 (the source proposal listed it as undecided).
- Which items make up the fixed policy set, and who writes them.
