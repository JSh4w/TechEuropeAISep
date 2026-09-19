"""Deterministic financial model: CAPEX, OPEX, financing, NPV and IRR for BESS."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from bessible.suitability.assumptions import FinanceAssumptions, Range

Duration = Literal[2, 4, 8]
IRR_UPPER = 5.0
IRR_ITERATIONS = 100


class CaseResult(BaseModel):
    """Evaluated financial returns and ranges for one storage duration."""

    duration_h: Duration
    capex_gbp: Range
    opex_gbp_year: Range
    revenue_gbp_year: Range
    npv_gbp: Range
    irr: Range | None
    payback_years: Range | None
    over_budget: bool
    curtailment_pct: float


def _npv(rate: float, flows: list[float]) -> float:
    """Net present value with flow 0 at time 0."""
    return sum(cf / ((1.0 + rate) ** year) for year, cf in enumerate(flows))


def _irr(flows: list[float]) -> float | None:
    """Compute IRR by bisection. Returns None if cash flows never pay back."""
    if flows[0] >= 0 or sum(flows) <= 0:
        return None
    low, high = -0.5, IRR_UPPER
    if _npv(high, flows) > 0:
        return None
    if _npv(low, flows) < 0:
        return None

    for _ in range(IRR_ITERATIONS):
        mid = (low + high) / 2
        val = _npv(mid, flows)
        if val > 0:
            low = mid
        else:
            high = mid
    res = (low + high) / 2
    return round(res, 4)


def _payback_years(flows: list[float]) -> float | None:
    """Simple payback in years from equity cash flows. None if never paid back."""
    cumulative = flows[0]
    if cumulative >= 0:
        return 0.0

    for year in range(1, len(flows)):
        prev = cumulative
        cumulative += flows[year]
        if cumulative >= 0:
            # Linear interpolation for fractional year
            fraction = (0 - prev) / (flows[year]) if flows[year] > 0 else 0.0
            return round(year - 1 + fraction, 2)
    return None


def _calc_single_bound(
    *,
    mw: float,
    duration_h: Duration,
    distance_km: float,
    firm_mw: float,
    battery_cost: float,
    bop_cost: float,
    cable_cost: float,
    opex_mw: float,
    revenue_mw: float,
    availability_pct: float,
    curtailment_haircut: float,
    debt_share_pct: float,
    interest_rate_pct: float,
    arrangement_fee_pct: float,
    discount_rate_pct: float,
    loan_term: int,
    project_life: int,
) -> tuple[float, float, float, float, float | None, float | None, float]:
    """Calculate single scenario point (low, mid, or high).

    Returns:
        (capex, opex, revenue, npv, irr, payback_years, curtailment_pct)
    """
    capex = (battery_cost * duration_h * mw) + (bop_cost * mw) + (cable_cost * distance_km)
    opex = opex_mw * mw

    curtail_frac = max(0.0, (mw - firm_mw) / mw) * curtailment_haircut if mw > 0 else 0.0
    curtail_pct = curtail_frac * 100.0

    revenue = revenue_mw * mw * (availability_pct / 100.0) * (1.0 - curtail_frac)

    # Debt financing
    debt = capex * (debt_share_pct / 100.0)
    fee = debt * (arrangement_fee_pct / 100.0)
    r = interest_rate_pct / 100.0
    n = max(1, loan_term)
    if r == 0:
        annual_payment = debt / n
    else:
        annual_payment = debt * r / (1.0 - (1.0 + r) ** (-n))

    # Equity cash flows
    flows = [-(capex - debt + fee)]
    for year in range(1, project_life + 1):
        net_cf = revenue - opex
        if year <= n:
            net_cf -= annual_payment
        flows.append(net_cf)

    d_rate = discount_rate_pct / 100.0
    npv_val = _npv(d_rate, flows)
    irr_val = _irr(flows)
    pb_val = _payback_years(flows)

    return (
        round(capex, 2),
        round(opex, 2),
        round(revenue, 2),
        round(npv_val, 2),
        irr_val,
        pb_val,
        round(curtail_pct, 2),
    )


def evaluate(
    mw: float,
    duration_h: Duration,
    distance_km: float | None,
    firm_mw: float,
    budget_gbp: float | None,
    a: FinanceAssumptions,
) -> CaseResult:
    """Pure evaluation of financial returns and low/mid/high range (< 10 ms)."""
    dist = distance_km if distance_km is not None and distance_km > 0 else 0.5

    # Look up inputs by duration
    rev_key = f"revenue_{duration_h}h_gbp_per_mw_year"
    rev_r = a.range(rev_key)

    bat_r = a.range("battery_gbp_per_mwh")
    bop_r = a.range("balance_of_plant_gbp_per_mw")
    cab_r = a.range("cable_33kv_gbp_per_km")
    opx_r = a.range("opex_gbp_per_mw_year")
    avl_r = a.range("availability_pct")
    cur_r = a.range("curtailment_haircut")
    dbt_r = a.range("debt_share_pct")
    int_r = a.range("interest_rate_pct")
    fee_r = a.range("arrangement_fee_pct")
    dsc_r = a.range("discount_rate_pct")
    ltm_r = a.range("loan_term_years")
    plf_r = a.range("project_life_years")

    # Mid case
    (
        capex_mid,
        opex_mid,
        rev_mid,
        npv_mid,
        irr_mid,
        pb_mid,
        curtail_mid,
    ) = _calc_single_bound(
        mw=mw,
        duration_h=duration_h,
        distance_km=dist,
        firm_mw=firm_mw,
        battery_cost=bat_r.mid,
        bop_cost=bop_r.mid,
        cable_cost=cab_r.mid,
        opex_mw=opx_r.mid,
        revenue_mw=rev_r.mid,
        availability_pct=avl_r.mid,
        curtailment_haircut=cur_r.mid,
        debt_share_pct=dbt_r.mid,
        interest_rate_pct=int_r.mid,
        arrangement_fee_pct=fee_r.mid,
        discount_rate_pct=dsc_r.mid,
        loan_term=int(ltm_r.mid),
        project_life=int(plf_r.mid),
    )

    # Low case (pessimistic: high cost, low revenue, high financing costs)
    (
        capex_low_cf,
        opex_low_cf,
        rev_low_cf,
        npv_low,
        irr_low,
        pb_low,
        _,
    ) = _calc_single_bound(
        mw=mw,
        duration_h=duration_h,
        distance_km=dist,
        firm_mw=firm_mw,
        battery_cost=bat_r.high,
        bop_cost=bop_r.high,
        cable_cost=cab_r.high,
        opex_mw=opx_r.high,
        revenue_mw=rev_r.low,
        availability_pct=avl_r.low,
        curtailment_haircut=cur_r.high,
        debt_share_pct=dbt_r.low,
        interest_rate_pct=int_r.high,
        arrangement_fee_pct=fee_r.high,
        discount_rate_pct=dsc_r.high,
        loan_term=int(ltm_r.low),
        project_life=int(plf_r.low),
    )

    # High case (optimistic: low cost, high revenue, favorable financing)
    (
        capex_high_cf,
        opex_high_cf,
        rev_high_cf,
        npv_high,
        irr_high,
        pb_high,
        _,
    ) = _calc_single_bound(
        mw=mw,
        duration_h=duration_h,
        distance_km=dist,
        firm_mw=firm_mw,
        battery_cost=bat_r.low,
        bop_cost=bop_r.low,
        cable_cost=cab_r.low,
        opex_mw=opx_r.low,
        revenue_mw=rev_r.high,
        availability_pct=avl_r.high,
        curtailment_haircut=cur_r.low,
        debt_share_pct=dbt_r.high,
        interest_rate_pct=int_r.low,
        arrangement_fee_pct=fee_r.low,
        discount_rate_pct=dsc_r.low,
        loan_term=int(ltm_r.high),
        project_life=int(plf_r.high),
    )

    over_budget = bool(budget_gbp is not None and capex_mid > budget_gbp)

    # Range for capex/opex/revenue ordered min..max
    capex_range = Range(
        low=min(capex_low_cf, capex_high_cf),
        mid=capex_mid,
        high=max(capex_low_cf, capex_high_cf),
    )
    opex_range = Range(
        low=min(opex_low_cf, opex_high_cf),
        mid=opex_mid,
        high=max(opex_low_cf, opex_high_cf),
    )
    rev_range = Range(
        low=min(rev_low_cf, rev_high_cf),
        mid=rev_mid,
        high=max(rev_low_cf, rev_high_cf),
    )
    npv_range = Range(
        low=min(npv_low, npv_high),
        mid=npv_mid,
        high=max(npv_low, npv_high),
    )

    irr_range: Range | None = None
    if irr_mid is not None:
        irr_range = Range(
            low=min(x for x in [irr_low or irr_mid, irr_mid, irr_high or irr_mid]),
            mid=irr_mid,
            high=max(x for x in [irr_low or irr_mid, irr_mid, irr_high or irr_mid]),
        )

    pb_range: Range | None = None
    if pb_mid is not None:
        pb_range = Range(
            low=min(x for x in [pb_low or pb_mid, pb_mid, pb_high or pb_mid]),
            mid=pb_mid,
            high=max(x for x in [pb_low or pb_mid, pb_mid, pb_high or pb_mid]),
        )

    return CaseResult(
        duration_h=duration_h,
        capex_gbp=capex_range,
        opex_gbp_year=opex_range,
        revenue_gbp_year=rev_range,
        npv_gbp=npv_range,
        irr=irr_range,
        payback_years=pb_range,
        over_budget=over_budget,
        curtailment_pct=curtail_mid,
    )
