"""Market revenue projections stage placeholder."""

from __future__ import annotations

import asyncio

from pydantic import HttpUrl

from bessible.models import Artifact, MarketOutput, NodeInput

DEFAULT_REVENUE_GBP_PER_MW_YEAR = 65000.0
DEFAULT_STREAMS = {
    "dynamic_containment": 25000.0,
    "wholesale_arbitrage": 30000.0,
    "capacity_market": 10000.0,
}


async def market_revenue(inp: NodeInput) -> MarketOutput:
    """Project revenue streams across ancillary services, trading, and capacity market."""
    await asyncio.sleep(0)

    art = Artifact(
        id=f"market-{inp.run_id[:8]}",
        stage="market",
        claim=(
            f"Estimated revenue of £{DEFAULT_REVENUE_GBP_PER_MW_YEAR:,.0f}/MW/year "
            "across wholesale arbitrage, dynamic containment, and capacity market"
        ),
        source_url=HttpUrl("https://bmreports.com"),
        confidence=0.85,
        model_used="dummy",
    )

    return MarketOutput(
        revenue_gbp_per_mw_year=DEFAULT_REVENUE_GBP_PER_MW_YEAR,
        streams=dict(DEFAULT_STREAMS),
        artifacts=[art],
    )
