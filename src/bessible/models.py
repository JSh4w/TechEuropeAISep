"""Pydantic models shared by the workflow, activities and (as JSON) the web frontend.

Field names are the JSON contract with `web/`: keep them snake_case and in sync with `web/lib/types.ts`.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class Artifact(BaseModel):
    """One piece of evidence behind a claim (explainable AI)."""

    step: str
    claim: str
    source: str  # URL or local file path
    confidence: float
    model: str | None = None  # which model produced it, if any


class Polygon(BaseModel):
    """GeoJSON Polygon geometry. Coordinates are [lng, lat]; the first ring is the outline, closed."""

    type: Literal["Polygon"] = "Polygon"
    coordinates: list[list[list[float]]]


class AssessmentInput(BaseModel):
    """What the user asks for when starting a session."""

    property_url: str
    lat: float = 51.6075  # dummy default: Didcot
    lng: float = -1.2410
    battery_mw: float = 5.0
    budget_gbp: int = 2_000_000


class AreaSuggestion(BaseModel):
    """The AI agent's proposed battery area within the title boundary."""

    area: Polygon
    title_boundary: Polygon
    rationale: str
    artifacts: list[Artifact] = Field(default_factory=list)


class AreaFeedback(BaseModel):
    """Validation result for an area, shown on the map after every edit."""

    ok: bool
    area_m2: float
    capacity_mw: float
    issues: list[str] = Field(default_factory=list)


class ValidateInput(BaseModel):
    """Input to `validate_area`."""

    inp: AssessmentInput
    area: Polygon
    title_boundary: Polygon


class EngineResult(BaseModel):
    """Output of the feasibility or suitability engine."""

    score: float  # 0-1
    summary: str
    artifacts: list[Artifact] = Field(default_factory=list)


class EngineInput(BaseModel):
    """Input to the feasibility and suitability engines: the confirmed area."""

    inp: AssessmentInput
    area: Polygon
    feedback: AreaFeedback


Stage = Literal["suggesting", "awaiting_human", "assessing", "done"]


class SessionState(BaseModel):
    """Everything the map needs to render. Returned by the `state` query."""

    stage: Stage = "suggesting"
    step: str = "starting"  # human-readable current step
    input: AssessmentInput | None = None
    title_boundary: Polygon | None = None
    suggested_area: Polygon | None = None
    suggestion_rationale: str = ""
    current_area: Polygon | None = None
    feedback: AreaFeedback | None = None
    edits: int = 0
    feasibility: EngineResult | None = None
    suitability: EngineResult | None = None
    verdict: str | None = None
    artifacts: list[Artifact] = Field(default_factory=list)
