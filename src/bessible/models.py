"""Typed data that flows between assessment stages.

Owned by Josh. Change models only by ADDING optional fields, and tell the team.
Every stage output carries `artifacts`: the evidence behind each claim (explainable AI).
"""

from __future__ import annotations

from typing import Any, Literal, Self

from pydantic import BaseModel, Field, HttpUrl, ValidationInfo, model_validator

Stage = Literal["location", "capacity", "title", "grid", "site_land", "market", "financial", "planning", "synthesis"]
Verdict = Literal["go", "maybe", "no_go"]
Duration = Literal[2, 4, 8]
DURATIONS: tuple[Duration, ...] = (2, 4, 8)


class AssessmentRequest(BaseModel):
    """What the user asks for: a property link and/or a UK postcode, plus optional intent."""

    property_url: HttpUrl | None = None
    postcode: str | None = None
    battery_mw: float | None = Field(default=None, gt=0)
    budget_gbp: float | None = Field(default=None, gt=0)
    flexible_connection: bool = False

    @model_validator(mode="after")
    def _needs_site(self) -> Self:
        if self.property_url is None and not self.postcode:
            msg = "Give a property link or a postcode"
            raise ValueError(msg)
        return self


class Position(BaseModel):
    """A point on the map (WGS84)."""

    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)


class Artifact(BaseModel):
    """One piece of evidence behind a claim. Needs at least one of source_url / file_path / image_path."""

    id: str  # "<stage>-<n>", unique per run
    stage: Stage
    claim: str
    source_url: HttpUrl | None = None
    file_path: str | None = None  # relative to out/<run_id>/
    image_path: str | None = None  # relative to out/<run_id>/
    confidence: float = Field(ge=0, le=1)
    model_used: str  # e.g. "gemini-3.8-flash", "open-jev-deberta-v3-large (Modal)", "ukpn-snapshot", "dummy"

    @model_validator(mode="after")
    def _needs_evidence(self) -> Self:
        if self.source_url is None and self.file_path is None and self.image_path is None:
            msg = "An artifact needs a source_url, file_path or image_path"
            raise ValueError(msg)
        return self


class StageInput(BaseModel):
    """Common input for every stage."""

    run_id: str
    request: AssessmentRequest


# --- Before confirmation (feasibility) ---------------------------------------------------------


class LocationInput(StageInput):
    """Input to `resolve_location`."""


class LocationOutput(BaseModel):
    """Where the site is."""

    postcode: str
    position: Position
    artifacts: list[Artifact]


class CapacityInput(StageInput):
    """Input to `propose_capacity`."""

    location: LocationOutput


class CapacityOutput(BaseModel):
    """How many MW could connect, as a range, and what limits it."""

    viable: bool
    message: str | None = None  # required when not viable
    out_of_area: bool = False  # implies viable == False
    substation: str | None = None
    connection_voltage_kv: float | None = None
    firm_mw: float = Field(ge=0)
    ceiling_mw: float = Field(ge=0)
    recommended_mw: float = Field(ge=0)
    binding_direction: Literal["import", "export"] | None = None
    binding_season: Literal["winter", "summer"] | None = None
    distance_km: float | None = Field(default=None, ge=0)
    artifacts: list[Artifact]

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        if self.ceiling_mw < self.firm_mw:
            msg = f"ceiling_mw ({self.ceiling_mw}) is below firm_mw ({self.firm_mw})"
            raise ValueError(msg)
        if self.out_of_area and self.viable:
            msg = "An out-of-area site cannot be viable"
            raise ValueError(msg)
        if not self.viable and not self.message:
            msg = "A non-viable capacity needs a message saying why"
            raise ValueError(msg)
        return self


class TitleInput(StageInput):
    """Input to `find_title_boundaries`."""

    location: LocationOutput
    capacity: CapacityOutput


class TitleOutput(BaseModel):
    """The registered title boundary for the site."""

    title_number: str
    boundary_geojson: dict[str, Any]
    area_m2: float = Field(ge=0)
    artifacts: list[Artifact]


# --- Human in the loop -------------------------------------------------------------------------


class SiteDecision(BaseModel):
    """Sent by the CLI or web UI to confirm or reject the site."""

    confirmed: bool
    position: Position | None = None  # None = proposal default
    capacity_mw: float | None = Field(default=None, gt=0)  # None = capacity.recommended_mw


class ConfirmedSite(BaseModel):
    """Built by the workflow once the user confirms.

    Validate with context `{"capacity": CapacityOutput, "flexible": bool}` (see `ConfirmedSite.build`)
    to check the capacity against the proposal's range.
    """

    position: Position
    capacity_mw: float = Field(gt=0)
    boundary: TitleOutput
    footprint_geojson: dict[str, Any] | None = None  # None until a map step exists

    @model_validator(mode="after")
    def _within_range(self, info: ValidationInfo) -> Self:
        ctx = info.context or {}
        capacity: CapacityOutput | None = ctx.get("capacity")
        if capacity is None:
            return self
        max_mw = capacity.ceiling_mw if ctx.get("flexible") else capacity.firm_mw
        if self.capacity_mw > max_mw:
            msg = f"Capacity {self.capacity_mw} MW is above the allowed maximum of {max_mw} MW"
            raise ValueError(msg)
        return self

    @classmethod
    def build(cls, *, capacity: CapacityOutput, flexible: bool, **fields: Any) -> ConfirmedSite:  # ruff: ignore[any-type]
        """Construct and validate against the capacity proposal."""
        return cls.model_validate(fields, context={"capacity": capacity, "flexible": flexible})


# --- After confirmation (analysis) -------------------------------------------------------------


class NodeInput(StageInput):
    """Input to every stage after confirmation."""

    site: ConfirmedSite
    capacity: CapacityOutput


class GridOutput(BaseModel):
    """Grid connection context: queue position and timescales."""

    gate2_queue_position: int | None = None
    indicative_connection_months: int | None = None
    artifacts: list[Artifact]


class SiteLandOutput(BaseModel):
    """Land use and constraints on the site."""

    land_use: str
    constraints: list[str]
    artifacts: list[Artifact]


class MarketOutput(BaseModel):
    """Revenue available to the battery."""

    revenue_gbp_per_mw_year: float
    streams: dict[str, float]
    artifacts: list[Artifact]


class FinancialInput(NodeInput):
    """Input to `financial_model`."""

    grid: GridOutput
    market: MarketOutput


class DurationCase(BaseModel):
    """Returns for one battery duration."""

    duration_h: Duration
    capex_gbp: float
    npv_gbp: float
    irr: float | None = None  # None when it never pays back


class FinancialOutput(BaseModel):
    """Exactly one case each for 2, 4 and 8 hours."""

    cases: list[DurationCase]
    artifacts: list[Artifact]

    @model_validator(mode="after")
    def _three_durations(self) -> Self:
        if sorted(c.duration_h for c in self.cases) != list(DURATIONS):
            msg = "Financial output needs exactly one case each for 2, 4 and 8 hours"
            raise ValueError(msg)
        return self


class PlanningInput(NodeInput):
    """Input to `regulatory_planning`."""

    grid: GridOutput
    site_land: SiteLandOutput


class PlanningOutput(BaseModel):
    """Consenting route and planning risks."""

    consenting_route: str
    risks: list[str]
    artifacts: list[Artifact]


class Finding(BaseModel):
    """One statement in the report, citing the artifacts behind it."""

    text: str
    artifact_ids: list[str] = Field(min_length=1)


class SynthesisInput(NodeInput):
    """Everything the report is built from."""

    grid: GridOutput
    site_land: SiteLandOutput
    market: MarketOutput
    financial: FinancialOutput
    planning: PlanningOutput
    artifacts: list[Artifact]  # every artifact so far


class ReportOutput(BaseModel):
    """The verdict and its findings."""

    verdict: Verdict
    findings: list[Finding]
    report_path: str  # relative to out/<run_id>/
    artifacts: list[Artifact]


# --- Run state ---------------------------------------------------------------------------------

RunState = Literal["running", "awaiting_confirmation", "completed", "rejected", "out_of_area", "not_viable", "failed"]


class RunStatus(BaseModel):
    """Returned by the workflow's `status` query."""

    status: RunState
    stages: list[Stage]  # stages running now
    capacity: CapacityOutput | None = None  # set once known
    boundary: TitleOutput | None = None  # set while awaiting_confirmation


class AssessmentResult(BaseModel):
    """What a finished run returns."""

    status: Literal["completed", "rejected", "out_of_area", "not_viable"]
    message: str | None = None  # set for out_of_area / not_viable
    report: ReportOutput | None = None
    financial: FinancialOutput | None = None
    artifacts: list[Artifact]
    run_dir: str
