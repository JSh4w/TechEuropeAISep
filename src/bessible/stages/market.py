"""Market revenue projections stage: sourced streams, de-rating, and long-duration support."""

from __future__ import annotations

from bessible.market import load_market_assumptions
from bessible.market.sources import default_sources
from bessible.market.stack import revenue_stack, total
from bessible.models import Artifact, MarketOutput, NodeInput


async def market_revenue(inp: NodeInput) -> MarketOutput:
    """Project revenue streams across ancillary services, trading, capacity market, and support schemes."""
    a = load_market_assumptions()
    sources = default_sources()
    mw = inp.site.capacity_mw

    stack = await revenue_stack(mw, sources, a)
    four_hour_rows = stack.get(4, [])
    revenue_4h = total(four_hour_rows)
    streams_4h = {r.stream: r.gbp_per_mw_year for r in four_hour_rows}

    # Generate one artifact per stream across all durations
    seen_streams: set[str] = set()
    artifacts: list[Artifact] = []

    # Priority order of durations to select stream values from
    for duration_h in (4, 2, 8):
        for val in stack.get(duration_h, []):
            if val.stream in seen_streams:
                continue
            seen_streams.add(val.stream)

            if val.scheme:
                claim = (
                    f"{val.scheme}: estimated £{val.gbp_per_mw_year:,.0f}/MW/year under {val.scheme} "
                    f"support scheme (source: {val.source}, as of {val.as_of.isoformat()})"
                )
            elif val.cached:
                claim = (
                    f"{val.stream.replace('_', ' ').title()}: estimated £{val.gbp_per_mw_year:,.0f}/MW/year "
                    f"(4h basis) from {val.source} (cached fixture as of {val.as_of.isoformat()})"
                )
            else:
                claim = (
                    f"{val.stream.replace('_', ' ').title()}: estimated £{val.gbp_per_mw_year:,.0f}/MW/year "
                    f"(4h basis) from {val.source} as of {val.as_of.isoformat()}"
                )

            confidence = 0.85 if (val.placeholder or val.cached) else 1.0
            artifacts.append(
                Artifact(
                    id=f"market-{val.stream}-{inp.run_id[:8]}",
                    stage="market",
                    claim=claim,
                    source_url=val.source_url,
                    confidence=confidence,
                    model_used="market-assumptions",
                )
            )

    return MarketOutput(
        revenue_gbp_per_mw_year=revenue_4h,
        streams=streams_4h,
        by_duration=stack,
        artifacts=artifacts,
    )
