"""Temporal activity wrappers for assessment stages."""

from __future__ import annotations

from pydantic import ValidationError
from temporalio import activity
from temporalio.exceptions import ApplicationError

from bessible import events, stages
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
    SentimentOutput,
    SiteLandOutput,
    SynthesisInput,
    TitleInput,
    TitleOutput,
)
from bessible.ukpn.snapshot import SnapshotNotFoundError


@activity.defn
async def resolve_location(inp: LocationInput) -> LocationOutput:
    """Temporal activity for location resolution stage."""
    events.emit(inp.run_id, "location", "Resolving site location and postcode")
    try:
        res = await stages.location.resolve_location(inp)
    except ValidationError as exc:
        raise ApplicationError(str(exc), type="ValidationError", non_retryable=True) from exc
    except PostcodeNotFoundError as exc:
        raise ApplicationError(str(exc), type="PostcodeNotFound", non_retryable=True) from exc
    else:
        events.emit(
            inp.run_id,
            "location",
            f"Location resolved: {res.postcode} ({res.position.lat:.4f}, {res.position.lon:.4f})",
        )
        return res


@activity.defn
async def propose_capacity(inp: CapacityInput) -> CapacityOutput:
    """Temporal activity for grid capacity proposal stage."""
    events.emit(inp.run_id, "capacity", "Evaluating grid capacity and primary substations")
    try:
        res = await stages.capacity.propose_capacity(inp)
    except ValidationError as exc:
        raise ApplicationError(str(exc), type="ValidationError", non_retryable=True) from exc
    except SnapshotNotFoundError as exc:
        raise ApplicationError(str(exc), type="SnapshotNotFound", non_retryable=True) from exc
    else:
        events.emit(
            inp.run_id,
            "capacity",
            f"Grid capacity evaluated: {res.recommended_mw:g} MW at {res.substation or 'unknown'} "
            f"({'viable' if res.viable else 'not viable'})",
        )
        return res


@activity.defn
async def find_title_boundaries(inp: TitleInput) -> TitleOutput:
    """Temporal activity for title boundary lookup stage."""
    events.emit(inp.run_id, "title", "Querying HM Land Registry for title boundaries")
    try:
        res = await stages.title.find_title_boundaries(inp)
    except ValidationError as exc:
        raise ApplicationError(str(exc), type="ValidationError", non_retryable=True) from exc
    else:
        events.emit(
            inp.run_id,
            "title",
            f"Title boundary identified: {res.title_number} ({res.area_m2:,.0f} m²)",
        )
        return res


@activity.defn
async def grid_connection(inp: NodeInput) -> GridOutput:
    """Temporal activity for grid connection stage."""
    events.emit(inp.run_id, "grid", "Assessing grid connection queue and timescales")
    try:
        res = await stages.grid.grid_connection(inp)
    except ValidationError as exc:
        raise ApplicationError(str(exc), type="ValidationError", non_retryable=True) from exc
    else:
        events.emit(
            inp.run_id,
            "grid",
            f"Grid connection assessment complete (Gate 2 position: {res.gate2_queue_position or 'N/A'})",
        )
        return res


@activity.defn
async def site_land(inp: NodeInput) -> SiteLandOutput:
    """Temporal activity for site and land assessment stage."""
    events.emit(inp.run_id, "site_land", "Analyzing environmental constraints and land classification")
    try:
        res = await stages.site_land.site_land(inp)
    except ValidationError as exc:
        raise ApplicationError(str(exc), type="ValidationError", non_retryable=True) from exc
    else:
        events.emit(
            inp.run_id,
            "site_land",
            f"Site land constraints assessed: {len(res.constraints)} constraints noted",
        )
        return res


@activity.defn
async def market_revenue(inp: NodeInput) -> MarketOutput:
    """Temporal activity for market revenue stage."""
    events.emit(inp.run_id, "market", "Modeling wholesale, capacity market, and ancillary service revenues")
    try:
        res = await stages.market.market_revenue(inp)
    except ValidationError as exc:
        raise ApplicationError(str(exc), type="ValidationError", non_retryable=True) from exc
    else:
        events.emit(
            inp.run_id,
            "market",
            f"Market revenue projected: £{res.revenue_gbp_per_mw_year:,.0f}/MW/yr",
        )
        return res


@activity.defn
async def financial_model(inp: FinancialInput) -> FinancialOutput:
    """Temporal activity for financial modeling stage."""
    events.emit(inp.run_id, "financial", "Simulating 25-year financial models across 2h, 4h, and 8h durations")
    try:
        res = await stages.financial.financial_model(inp)
    except ValidationError as exc:
        raise ApplicationError(str(exc), type="ValidationError", non_retryable=True) from exc
    else:
        events.emit(
            inp.run_id,
            "financial",
            f"Financial returns modeled (recommended: {res.recommended_h}h duration)",
        )
        return res


@activity.defn
async def regulatory_planning(inp: PlanningInput) -> PlanningOutput:
    """Temporal activity for regulatory and planning stage."""
    events.emit(inp.run_id, "planning", "Evaluating consenting routes and planning risk profile")
    try:
        res = await stages.planning.regulatory_planning(inp)
    except ValidationError as exc:
        raise ApplicationError(str(exc), type="ValidationError", non_retryable=True) from exc
    else:
        events.emit(
            inp.run_id,
            "planning",
            f"Consenting route determined: {res.consenting_route}",
        )
        return res


@activity.defn
async def synthesise(inp: SynthesisInput) -> ReportOutput:
    """Temporal activity for synthesis stage."""
    events.emit(inp.run_id, "synthesis", "Synthesising final recommendation and generating assessment report")
    try:
        res = await stages.synthesis.synthesise(inp)
    except ValidationError as exc:
        raise ApplicationError(str(exc), type="ValidationError", non_retryable=True) from exc
    else:
        events.emit(
            inp.run_id,
            "synthesis",
            f"Assessment complete: overall verdict {res.verdict.upper()}",
        )
        return res


@activity.defn
async def local_sentiment(inp: NodeInput) -> SentimentOutput:
    """Temporal activity for local community sentiment analysis stage."""
    events.emit(inp.run_id, "sentiment", "Analyzing local community sentiment and planning records")
    try:
        res = await stages.sentiment.local_sentiment(inp)
    except ValidationError as exc:
        raise ApplicationError(str(exc), type="ValidationError", non_retryable=True) from exc
    else:
        opp_str = f"{res.opposition_index:.2f}" if res.opposition_index is not None else "N/A"
        events.emit(
            inp.run_id,
            "sentiment",
            f"Local sentiment assessed (opposition index: {opp_str})",
        )
        return res


ALL_ACTIVITIES = [
    resolve_location,
    propose_capacity,
    find_title_boundaries,
    grid_connection,
    site_land,
    market_revenue,
    local_sentiment,
    financial_model,
    regulatory_planning,
    synthesise,
]
