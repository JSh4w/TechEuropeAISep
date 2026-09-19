"""Financial model assessment stage placeholder."""

from __future__ import annotations

import asyncio

from pydantic import HttpUrl

from bessible.models import Artifact, DurationCase, FinancialInput, FinancialOutput

CAPEX_PER_MW_2H = 500_000.0
CAPEX_PER_MW_4H = 875_000.0
CAPEX_PER_MW_8H = 1_580_000.0

NPV_PER_MW_2H = 100_000.0
NPV_PER_MW_4H = 175_000.0
NPV_PER_MW_8H = 260_000.0

IRR_2H = 0.11
IRR_4H = 0.13
IRR_8H = 0.09


async def financial_model(inp: FinancialInput) -> FinancialOutput:
    """Evaluate financial returns across 2-hour, 4-hour, and 8-hour duration cases."""
    await asyncio.sleep(0)
    mw = inp.site.capacity_mw

    cases = [
        DurationCase(
            duration_h=2,
            capex_gbp=round(mw * CAPEX_PER_MW_2H, 2),
            npv_gbp=round(mw * NPV_PER_MW_2H, 2),
            irr=IRR_2H,
        ),
        DurationCase(
            duration_h=4,
            capex_gbp=round(mw * CAPEX_PER_MW_4H, 2),
            npv_gbp=round(mw * NPV_PER_MW_4H, 2),
            irr=IRR_4H,
        ),
        DurationCase(
            duration_h=8,
            capex_gbp=round(mw * CAPEX_PER_MW_8H, 2),
            npv_gbp=round(mw * NPV_PER_MW_8H, 2),
            irr=IRR_8H,
        ),
    ]

    art = Artifact(
        id=f"financial-{inp.run_id[:8]}",
        stage="financial",
        claim="4-hour duration yields optimal IRR at 13.0% with positive 25-year NPV",
        source_url=HttpUrl("https://www.eex.com"),
        confidence=0.89,
        model_used="dummy",
    )

    return FinancialOutput(cases=cases, artifacts=[art])
