"""UKPN connection competition assessment: offers not accepted, budget estimates, and enquiries."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bessible.ukpn.models import Competition

if TYPE_CHECKING:
    from bessible.ukpn.snapshot import Snapshot

WEIGHTS = {"offers": 0.5, "budget": 0.25, "enquiries": 0.1}


def _norm(s: str | None) -> str:
    return s.strip().lower() if s else ""


def competition(sub: Any, snap: Snapshot, effective_headroom: float = 0.0) -> Competition:  # ruff: ignore[any-type]
    """Assess competing connection interest at a substation. Does not subtract from headroom."""
    sub_name = getattr(sub, "name", None) or ""
    norm_name = _norm(sub_name)

    offers = (getattr(sub, "generationconnectionoffersmadecapacity", None) or 0.0) + (
        getattr(sub, "loadconnectionoffersmadecapacity", None) or 0.0
    )
    budget = (getattr(sub, "generationbudgetestimatesprovidedcapacity", None) or 0.0) + (
        getattr(sub, "loadbudgetestimatesprovidedcapacity", None) or 0.0
    )
    enquiries = 0.0

    # Look up LTDS Table 6 interest records
    for r in snap.table6_records:
        if _norm(r.substation) == norm_name or (_norm(r.substation) in norm_name and norm_name):
            status = _norm(r.status_of_connection)
            cap = (r.demand_numbers_received_total_capacity or 0.0) + (
                r.generation_numbers_received_total_capacity or 0.0
            )
            if "not yet accepted" in status or "offers made" in status:
                offers = max(offers, cap)
            elif "budget" in status:
                budget = max(budget, cap)
            else:
                enquiries += cap

    weighted = (offers * WEIGHTS["offers"]) + (budget * WEIGHTS["budget"]) + (enquiries * WEIGHTS["enquiries"])
    weighted_mw = round(weighted, 2)

    if effective_headroom <= 0:
        pressure = "high" if weighted_mw > 0 else "low"
    elif weighted_mw < 0.5 * effective_headroom:
        pressure = "low"
    elif weighted_mw < 1.0 * effective_headroom:
        pressure = "medium"
    else:
        pressure = "high"

    return Competition(
        offers_not_accepted_mw=round(offers, 2),
        budget_estimates_mw=round(budget, 2),
        enquiries_mw=round(enquiries, 2),
        weighted_mw=weighted_mw,
        pressure=pressure,
    )
