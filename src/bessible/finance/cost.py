"""CAPEX, OPEX and grid connection cost from documented assumptions."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel

if TYPE_CHECKING:
    from bessible.assumptions import AssumptionSet

Duration = Literal[2, 4, 8]


class CostBreakdown(BaseModel):
    """Cost of one duration case. `capex_gbp` uses the midpoint of each range."""

    duration_h: Duration
    mw: float
    battery_gbp: float
    balance_of_plant_gbp: float
    capex_gbp: float
    opex_gbp_per_year: float
    connection_gbp: tuple[float, float]
    crossing_uplift_applied: bool
    otcf_gbp: tuple[float, float] | None = None
    otcf_state: str = ""


def _otcf_state(oversubscription_pct: float, on_above: float, off_below: float) -> tuple[bool, str]:
    if oversubscription_pct > on_above:
        return (
            True,
            f"active (oversubscription {oversubscription_pct:g}% is above {on_above:g}%), proposed, not in force",
        )
    if oversubscription_pct < off_below:
        return False, f"inactive (oversubscription {oversubscription_pct:g}% is below {off_below:g}%)"
    return False, f"inactive (oversubscription {oversubscription_pct:g}% is between {off_below:g}% and {on_above:g}%)"


VOLTAGE_132KV = 132


def cost(  # ruff: ignore[too-many-arguments]
    duration_h: Duration,
    mw: float,
    distance_km: float,
    *,
    crossings: bool,
    a: AssumptionSet,
    voltage_kv: float | None = None,
) -> CostBreakdown:
    """Compute cost for one duration. Raises `MissingAssumption` naming any absent key."""
    battery = a.number("battery_gbp_per_mwh") * duration_h * mw
    bop = a.number("balance_of_plant_gbp_per_mw") * mw
    opex = a.number("opex_gbp_per_mw_year") * mw

    cable_key = "cable_132kv_gbp_per_km" if voltage_kv == VOLTAGE_132KV else "cable_33kv_gbp_per_km"
    cable_low, cable_high = a.pair(cable_key)
    uplift = 1 + a.number("crossing_uplift_pct") / 100 if crossings else 1.0
    connection = (cable_low * distance_km * uplift, cable_high * distance_km * uplift)

    fee_low, fee_high = a.pair("otcf_gbp_per_mw")
    active, state = _otcf_state(
        a.number("oversubscription_pct"), a.number("otcf_on_above_pct"), a.number("otcf_off_below_pct")
    )
    otcf = (fee_low * mw, fee_high * mw) if active else None

    capex = battery + bop + sum(connection) / 2 + (sum(otcf) / 2 if otcf else 0.0)
    return CostBreakdown(
        duration_h=duration_h,
        mw=mw,
        battery_gbp=battery,
        balance_of_plant_gbp=bop,
        capex_gbp=capex,
        opex_gbp_per_year=opex,
        connection_gbp=connection,
        crossing_uplift_applied=crossings,
        otcf_gbp=otcf,
        otcf_state=state,
    )
