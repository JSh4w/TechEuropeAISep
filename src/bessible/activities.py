"""Temporal activity wrappers for assessment stages."""

from __future__ import annotations

from pydantic import ValidationError
from temporalio import activity
from temporalio.exceptions import ApplicationError

from bessible import stages
from bessible.geocode import PostcodeNotFoundError
from bessible.models import (
    CapacityInput,
    CapacityOutput,
    FinancialInput,
    FinancialOutput,
    GridOutput,
    LocationInput,
    LocationOutput,
    MarketOutput,
    NodeInput,
    PlanningInput,
    PlanningOutput,
    ReportOutput,
    SiteLandOutput,
    SynthesisInput,
    TitleInput,
    TitleOutput,
)
from bessible.ukpn.snapshot import SnapshotNotFoundError


@activity.defn
async def resolve_location(inp: LocationInput) -> LocationOutput:
    """Temporal activity for location resolution stage."""
    try:
        return await stages.location.resolve_location(inp)
    except ValidationError as exc:
        raise ApplicationError(str(exc), type="ValidationError", non_retryable=True) from exc
    except PostcodeNotFoundError as exc:
        raise ApplicationError(str(exc), type="PostcodeNotFound", non_retryable=True) from exc


@activity.defn
async def propose_capacity(inp: CapacityInput) -> CapacityOutput:
    """Temporal activity for grid capacity proposal stage."""
    try:
        return await stages.capacity.propose_capacity(inp)
    except ValidationError as exc:
        raise ApplicationError(str(exc), type="ValidationError", non_retryable=True) from exc
    except SnapshotNotFoundError as exc:
        raise ApplicationError(str(exc), type="SnapshotNotFound", non_retryable=True) from exc


@activity.defn
async def find_title_boundaries(inp: TitleInput) -> TitleOutput:
    """Temporal activity for title boundary lookup stage."""
    try:
        return await stages.title.find_title_boundaries(inp)
    except ValidationError as exc:
        raise ApplicationError(str(exc), type="ValidationError", non_retryable=True) from exc


@activity.defn
async def grid_connection(inp: NodeInput) -> GridOutput:
    """Temporal activity for grid connection stage."""
    try:
        return await stages.grid.grid_connection(inp)
    except ValidationError as exc:
        raise ApplicationError(str(exc), type="ValidationError", non_retryable=True) from exc


@activity.defn
async def site_land(inp: NodeInput) -> SiteLandOutput:
    """Temporal activity for site and land assessment stage."""
    try:
        return await stages.site_land.site_land(inp)
    except ValidationError as exc:
        raise ApplicationError(str(exc), type="ValidationError", non_retryable=True) from exc


@activity.defn
async def market_revenue(inp: NodeInput) -> MarketOutput:
    """Temporal activity for market revenue stage."""
    try:
        return await stages.market.market_revenue(inp)
    except ValidationError as exc:
        raise ApplicationError(str(exc), type="ValidationError", non_retryable=True) from exc


@activity.defn
async def financial_model(inp: FinancialInput) -> FinancialOutput:
    """Temporal activity for financial modeling stage."""
    try:
        return await stages.financial.financial_model(inp)
    except ValidationError as exc:
        raise ApplicationError(str(exc), type="ValidationError", non_retryable=True) from exc


@activity.defn
async def regulatory_planning(inp: PlanningInput) -> PlanningOutput:
    """Temporal activity for regulatory and planning stage."""
    try:
        return await stages.planning.regulatory_planning(inp)
    except ValidationError as exc:
        raise ApplicationError(str(exc), type="ValidationError", non_retryable=True) from exc


@activity.defn
async def synthesise(inp: SynthesisInput) -> ReportOutput:
    """Temporal activity for synthesis stage."""
    try:
        return await stages.synthesis.synthesise(inp)
    except ValidationError as exc:
        raise ApplicationError(str(exc), type="ValidationError", non_retryable=True) from exc


ALL_ACTIVITIES = [
    resolve_location,
    propose_capacity,
    find_title_boundaries,
    grid_connection,
    site_land,
    market_revenue,
    financial_model,
    regulatory_planning,
    synthesise,
]
