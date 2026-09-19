"""Market revenue projections stage (simplified assumptions-driven)."""

from __future__ import annotations

import asyncio

from pydantic import HttpUrl

from bessible.models import Artifact, MarketOutput, NodeInput
from bessible.suitability.assumptions import load_finance_assumptions


async def market_revenue(inp: NodeInput) -> MarketOutput:
    """Project revenue streams for BESS across duration benchmarks."""
    await asyncio.sleep(0)
    assumptions = load_finance_assumptions()
    rev_4h = assumptions.range("revenue_4h_gbp_per_mw_year")

    # Mid 4h benchmark as reference revenue
    ref_revenue = rev_4h.mid

    art = Artifact(
        id=f"market-{inp.run_id[:8]}",
        stage="market",
        claim=(
            f"Benchmark market revenue of £{ref_revenue:,.0f}/MW/year (4h duration, range "
            f"£{rev_4h.low:,.0f} to £{rev_4h.high:,.0f}/MW/year) based on GB wholesale and ancillary market data"
        ),
        source_url=HttpUrl("https://modoenergy.com"),
        confidence=0.90,
        model_used="deterministic",
    )

    streams = {
        "wholesale_arbitrage": round(ref_revenue * 0.50, 2),
        "balancing_ancillary": round(ref_revenue * 0.35, 2),
        "capacity_market": round(ref_revenue * 0.15, 2),
    }

    return MarketOutput(
        revenue_gbp_per_mw_year=ref_revenue,
        streams=streams,
        artifacts=[art],
    )
