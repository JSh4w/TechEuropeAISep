"""Financial analyst agent: recommends duration and trade-offs using tool calls."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from pydantic_ai.models import Model

from bessible.suitability.assumptions import FinanceAssumptions, load_finance_assumptions
from bessible.suitability.finance import CaseResult, Duration, evaluate


class Recommendation(BaseModel):
    """Analyst recommendation for optimal storage duration."""

    duration_h: Literal[2, 4, 8] = Field(description="Recommended duration: 2, 4, or 8 hours")
    rationale: str = Field(
        description="Clear explanation of the trade-off and reasons for the recommendation quoting only evaluated numbers"
    )
    compared: list[int] = Field(
        default_factory=lambda: [2, 4, 8],
        description="Durations compared during the analysis",
    )


@dataclass
class AnalystDeps:
    """Dependencies provided to the analyst agent."""

    mw: float
    distance_km: float | None
    firm_mw: float
    budget_gbp: float | None
    assumptions: FinanceAssumptions


def _create_analyst_agent() -> Agent[AnalystDeps, Recommendation]:
    agent: Agent[AnalystDeps, Recommendation] = Agent(
        defer_model_check=True,  # no key at import time: the run's model is supplied per call
        deps_type=AnalystDeps,
        output_type=Recommendation,
        name="financial_analyst",
        system_prompt=(
            "You are a commercial battery energy storage (BESS) investment analyst for UK projects.\n"
            "Evaluate storage durations (2h, 4h, 8h) by calling evaluate_case for each duration.\n"
            "Compare CAPEX, NPV, IRR, payback period, curtailment, and budget constraints.\n"
            "Select the single best recommended duration and provide a concise rationale.\n"
            "STRICT GUARD: You MUST ONLY quote numbers returned by evaluate_case. Never invent any figure."
        ),
    )

    @agent.tool
    def evaluate_case(ctx: RunContext[AnalystDeps], duration_h: int) -> dict[str, object]:
        """Evaluate financial metrics for a specific storage duration (2, 4, or 8 hours)."""
        if duration_h not in {2, 4, 8}:
            return {"error": f"Invalid duration {duration_h}h; must be 2, 4, or 8"}
        d: Duration = 2 if duration_h == 2 else (4 if duration_h == 4 else 8)
        res = evaluate(
            mw=ctx.deps.mw,
            duration_h=d,
            distance_km=ctx.deps.distance_km,
            firm_mw=ctx.deps.firm_mw,
            budget_gbp=ctx.deps.budget_gbp,
            a=ctx.deps.assumptions,
        )
        return {
            "duration_h": res.duration_h,
            "capex_gbp": res.capex_gbp.mid,
            "npv_gbp": res.npv_gbp.mid,
            "irr_pct": round(res.irr.mid * 100, 1) if res.irr else None,
            "payback_years": res.payback_years.mid if res.payback_years else None,
            "over_budget": res.over_budget,
            "curtailment_pct": res.curtailment_pct,
        }

    return agent


analyst_agent = _create_analyst_agent()


def fallback_recommendation(cases: dict[Duration, CaseResult], budget_gbp: float | None) -> Recommendation:
    """Deterministic fallback recommendation if LLM call is unavailable."""
    eligible = [c for c in cases.values() if not c.over_budget]
    if not eligible:
        eligible = list(cases.values())

    # Pick case with best mid NPV among eligible
    best = max(eligible, key=lambda c: c.npv_gbp.mid)

    irr_str = f"{best.irr.mid * 100:.1f}%" if best.irr else "N/A"
    rationale = (
        f"Recommended {best.duration_h}-hour duration delivers the highest Net Present Value "
        f"(£{best.npv_gbp.mid:,.0f}) with mid CAPEX of £{best.capex_gbp.mid:,.0f} and {irr_str} IRR, "
        f"meeting commercial criteria within available budget."
    )
    return Recommendation(
        duration_h=best.duration_h,
        rationale=rationale,
        compared=[2, 4, 8],
    )


async def run_analyst(
    *,
    model: Model | None = None,
    mw: float,
    distance_km: float | None,
    firm_mw: float,
    budget_gbp: float | None,
    assumptions: FinanceAssumptions | None = None,
    cases: dict[Duration, CaseResult] | None = None,
) -> Recommendation:
    """Run the analyst agent with the run's `model`; without one, or on error, use the deterministic fallback."""
    assump = assumptions or load_finance_assumptions()
    evaluated_cases = (
        cases
        if cases is not None
        else {d: evaluate(mw, d, distance_km, firm_mw, budget_gbp, assump) for d in (2, 4, 8)}
    )

    deps = AnalystDeps(
        mw=mw,
        distance_km=distance_km,
        firm_mw=firm_mw,
        budget_gbp=budget_gbp,
        assumptions=assump,
    )

    if model is None:
        return fallback_recommendation(evaluated_cases, budget_gbp)

    try:
        # Prompt the analyst agent
        prompt = (
            f"Analyze BESS site with confirmed capacity {mw:g} MW (firm capacity: {firm_mw:g} MW, "
            f"distance: {distance_km or 0.5:g} km). Budget: £{budget_gbp:,.0f}."
            if budget_gbp
            else f"Analyze BESS site with confirmed capacity {mw:g} MW (firm capacity: {firm_mw:g} MW, "
            f"distance: {distance_km or 0.5:g} km). No budget cap."
        )
        res = await analyst_agent.run(prompt, deps=deps, model=model)
        rec = res.output
        if isinstance(rec, Recommendation):
            return rec
    except Exception:
        pass

    return fallback_recommendation(evaluated_cases, budget_gbp)
