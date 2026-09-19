"""Financial modeling assessment stage."""

from __future__ import annotations

from pydantic import HttpUrl

from bessible.models import Artifact, CaseBound, DurationCase, FinancialInput, FinancialOutput
from bessible.suitability.analyst import run_analyst
from bessible.suitability.assumptions import load_finance_assumptions
from bessible.suitability.finance import CaseResult, Duration, evaluate


async def financial_model(inp: FinancialInput) -> FinancialOutput:
    """Evaluate 2h, 4h, and 8h BESS storage durations using deterministic modeling and LLM analyst."""
    assumptions = load_finance_assumptions()
    mw = inp.site.capacity_mw
    firm_mw = inp.capacity.firm_mw
    distance_km = inp.capacity.distance_km
    budget_gbp = inp.request.budget_gbp

    durations: list[Duration] = [2, 4, 8]
    evaluated_cases: dict[Duration, CaseResult] = {
        d: evaluate(
            mw=mw,
            duration_h=d,
            distance_km=distance_km,
            firm_mw=firm_mw,
            budget_gbp=budget_gbp,
            a=assumptions,
        )
        for d in durations
    }

    # Run the analyst agent to recommend optimal duration
    recommendation = await run_analyst(
        mw=mw,
        distance_km=distance_km,
        firm_mw=firm_mw,
        budget_gbp=budget_gbp,
        assumptions=assumptions,
        cases=evaluated_cases,
    )

    cases: list[DurationCase] = []
    artifacts: list[Artifact] = []

    for d in durations:
        cr = evaluated_cases[d]
        irr_mid = cr.irr.mid if cr.irr else None
        pb_mid = cr.payback_years.mid if cr.payback_years else None

        low_bound = CaseBound(
            capex_gbp=cr.capex_gbp.low,
            npv_gbp=cr.npv_gbp.low,
            irr=cr.irr.low if cr.irr else None,
            payback_years=cr.payback_years.low if cr.payback_years else None,
        )
        high_bound = CaseBound(
            capex_gbp=cr.capex_gbp.high,
            npv_gbp=cr.npv_gbp.high,
            irr=cr.irr.high if cr.irr else None,
            payback_years=cr.payback_years.high if cr.payback_years else None,
        )

        case = DurationCase(
            duration_h=d,
            capex_gbp=cr.capex_gbp.mid,
            npv_gbp=cr.npv_gbp.mid,
            irr=irr_mid,
            over_budget=cr.over_budget,
            curtailment_pct=cr.curtailment_pct,
            payback_years=pb_mid,
            low=low_bound,
            high=high_bound,
        )
        cases.append(case)

        irr_str = f"{irr_mid * 100:.1f}%" if irr_mid is not None else "N/A"
        pb_str = f"{pb_mid:.1f} years" if pb_mid is not None else "Beyond 25 years"
        budget_note = " [OVER BUDGET]" if cr.over_budget else ""
        artifacts.append(
            Artifact(
                id=f"financial-case-{d}h-{inp.run_id[:8]}",
                stage="financial",
                claim=(
                    f"{d}-hour duration: mid CAPEX £{cr.capex_gbp.mid:,.0f}, 25-yr NPV £{cr.npv_gbp.mid:,.0f}, "
                    f"IRR {irr_str}, simple payback {pb_str}, curtailment {cr.curtailment_pct:.1f}%{budget_note}."
                ),
                source_url=HttpUrl("https://www.gov.uk/government/publications/energy-and-emissions-projections"),
                confidence=0.92,
                model_used="deterministic",
            )
        )

    # Assumptions & recommendation artifacts
    artifacts.extend([
        Artifact(
            id=f"financial-assumptions-{inp.run_id[:8]}",
            stage="financial",
            claim=(
                "Financial assessment based on documented assumptions in finance.json "
                "(screening estimate; not investment advice)."
            ),
            file_path="data/assumptions/finance.json",
            confidence=0.95,
            model_used="finance.json",
        ),
        Artifact(
            id=f"financial-rec-{inp.run_id[:8]}",
            stage="financial",
            claim=f"Recommended duration: {recommendation.duration_h}h. Rationale: {recommendation.rationale}",
            source_url=HttpUrl("https://deepmind.google/technologies/gemini/"),
            confidence=0.90,
            model_used="gemini-3.8-flash",
        ),
    ])

    return FinancialOutput(
        cases=cases,
        recommended_h=recommendation.duration_h,
        rationale=recommendation.rationale,
        artifacts=artifacts,
    )
