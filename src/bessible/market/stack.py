"""Per-duration revenue stack: sourced streams, Capacity Market de-rating, support streams."""

from __future__ import annotations

from bessible.assumptions import AssumptionSet
from bessible.market.sources import RevenueSource
from bessible.market.support import qualifying, support_stream
from bessible.models import REQUIRED_DURATION_HOURS, StreamValue


async def revenue_stack(mw: float, sources: list[RevenueSource], a: AssumptionSet) -> dict[int, list[StreamValue]]:
    """Return the streams for each of 2, 4 and 8 hours. Capacity Market is scaled by the de-rating factor."""
    derating = a.mapping("capacity_market_derating")
    stack: dict[int, list[StreamValue]] = {}
    for duration_h in REQUIRED_DURATION_HOURS:
        rows: list[StreamValue] = []
        for source in sources:
            value = await source.fetch(duration_h)
            if value.stream == "capacity_market":
                factor = derating[str(duration_h)]
                value = value.model_copy(update={"gbp_per_mw_year": value.gbp_per_mw_year * factor})
            rows.append(value)
        rows.extend(support_stream(name, a) for name in qualifying(duration_h, mw, a))
        stack[duration_h] = rows
    return stack


def total(rows: list[StreamValue]) -> float:
    """Sum of stream revenue in GBP per MW per year."""
    return sum(r.gbp_per_mw_year for r in rows)
