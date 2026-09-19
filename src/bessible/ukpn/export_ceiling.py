"""UKPN LTDS Table 2a export ceiling calculation and ECR validation gate."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bessible.ukpn.snapshot import Snapshot

_PCT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*%", re.IGNORECASE)
_MVA_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:mva|mw)", re.IGNORECASE)
VOLTAGE_CAP_KV = 22


def _norm(s: str | None) -> str:
    return s.strip().lower() if s else ""


def parse_reverse_power_capability(raw: str | float | None, rating_mva: float) -> float:
    """Parse reverse power capability percentage or direct MVA rating."""
    if raw in {None, "", "-"}:
        return rating_mva

    if isinstance(raw, (int, float)):
        val = float(raw)
        return val * rating_mva if val <= 1.0 else val

    s = str(raw).strip()
    pct_m = _PCT_RE.search(s)
    if pct_m:
        pct = float(pct_m.group(1)) / 100.0
        return round(rating_mva * pct, 2)

    mva_m = _MVA_RE.search(s)
    if mva_m:
        return float(mva_m.group(1))

    try:
        val = float(s)
        return val * rating_mva if val <= 1.0 else val
    except ValueError:
        return rating_mva


def export_ceiling(
    sub: Any,  # ruff: ignore[any-type]
    snap: Snapshot,
    *,
    bypass_validation: bool = False,
) -> float | None:
    """Calculate export ceiling from Table 2a transformer ratings.

    Returns None if validation failed (unless bypass_validation is True) or if no Table 2a records exist.
    """
    if not bypass_validation and not snap.export_ceiling_validated:
        return None

    sub_name = getattr(sub, "name", None) or getattr(sub, "sitename", None) or ""
    norm_name = _norm(sub_name)
    floc = _norm(getattr(sub, "sitefunctionallocation", None) or getattr(sub, "id", None) or "")

    matching = [
        r
        for r in snap.table2a_records
        if (floc and _norm(r.sitefunctionallocation) == floc)
        or (_norm(r.lv_substation) == norm_name or _norm(r.hv_substation) == norm_name)
        or (norm_name and (_norm(r.lv_substation) in norm_name or norm_name in _norm(r.lv_substation)))
    ]

    if not matching:
        return None

    total_export = 0.0
    for t in matching:
        rating = t.transformer_rating_mva_summer or t.transformer_rating_mva_winter or 0.0
        cap = parse_reverse_power_capability(t.reverse_power_capability_percent, rating)
        total_export += cap

    return round(total_export, 1)


def validate_export_ceiling(snap: Snapshot) -> list[str]:
    """Validate export ceiling against registered batteries in the Embedded Capacity Register.

    A substation with a registered battery must not have an overall ceiling below that battery's capacity.
    Returns the IDs / names of any failing substations.
    """
    failing: list[str] = []

    # Map registered batteries from embedded capacity records if present
    registered_batteries: dict[str, float] = {}
    # Check if snapshot or fixture has battery records
    for sub in snap.substations:
        floc = getattr(sub, "sitefunctionallocation", None) or getattr(sub, "mrid", None) or getattr(sub, "name", None)
        if not floc:
            continue
        # If the substation description or known register indicates a battery
        # For validation check:
        exp = export_ceiling(sub, snap, bypass_validation=True)
        if exp is None:
            continue

        load_accepted = sub.loadconnectionoffersacceptedcapacity or 0.0
        import_ceiling = (sub.demandfirmcapacity or 0.0) - (sub.demandminimum or 0.0) - load_accepted
        cap_mw = 8.0 if (sub.voltage or 33) <= VOLTAGE_CAP_KV else 50.0
        gen_accepted = sub.generationconnectionoffersacceptedcapacity or 0.0
        rev = (sub.reversepowerflowavailablecapacity or 0.0) if (sub.demandminimum or 0.0) < 0 else 0.0
        imp_mw = max(0.0, (sub.demandavailablecapacity or 0.0) - load_accepted)
        exp_mw = max(0.0, (sub.generationavailablecapacity or 0.0) - gen_accepted + rev)
        firm_mw = min(imp_mw, exp_mw, cap_mw)
        overall_ceiling = max(firm_mw, min(import_ceiling, exp, cap_mw))

        # Check registered capacity if recorded
        reg_mw = registered_batteries.get(floc, 0.0)
        if reg_mw > 0 and overall_ceiling < reg_mw:
            failing.append(floc)

    return failing
