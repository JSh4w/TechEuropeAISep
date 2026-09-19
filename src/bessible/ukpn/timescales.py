"""National Grid / UKPN GSP queue position and indicative connection timescales."""

from __future__ import annotations

import statistics
from collections import Counter
from typing import TYPE_CHECKING

from bessible.ukpn.models import GspQueue, Timescales

if TYPE_CHECKING:
    from bessible.ukpn.snapshot import Snapshot


def _normalize_gsp(name: str | None) -> str:
    """Normalize GSP name for case-insensitive and suffix-tolerant matching."""
    if not name:
        return ""
    s = name.strip().upper()
    for suffix in (" 132KV", " 400KV", " 33KV", " GSP", " SUBSTATION"):
        if s.endswith(suffix):
            s = s[: -len(suffix)].strip()
    return s


def gsp_queue(gsp_id: str | None, snap: Snapshot) -> GspQueue | None:
    """Queue figures at the parent Grid Supply Point. Returns None if unknown or no records."""
    if not gsp_id or not gsp_id.strip():
        return None

    target = _normalize_gsp(gsp_id)
    records = [
        r
        for r in snap.gsp_project_status
        if _normalize_gsp(r.gsp) == target or target in _normalize_gsp(r.gsp) or _normalize_gsp(r.gsp) in target
    ]
    if not records:
        return None

    count_rows = [r for r in records if r.measure == "#"]
    mw_rows = [r for r in records if r.measure == "MW"]

    if count_rows or mw_rows:
        total_count_row = next((r for r in count_rows if (r.technology_type or "").upper() == "TOTAL"), None)
        if total_count_row:
            by_status = {
                "Gate 2 - Protected 26-27": int(total_count_row.gate_2_protected_26_27 or 0),
                "Gate 2 Phase 1": int(total_count_row.gate_2_phase_1 or 0),
                "Gate 2 Phase 2": int(total_count_row.gate_2_phase_2 or 0),
                "Gate 1": int(total_count_row.gate_1 or 0),
                "Has not undergone Gated process": int(total_count_row.has_not_undergone_gated_process or 0),
            }
        else:
            by_status = {
                "Gate 2 - Protected 26-27": int(sum(r.gate_2_protected_26_27 or 0 for r in count_rows)),
                "Gate 2 Phase 1": int(sum(r.gate_2_phase_1 or 0 for r in count_rows)),
                "Gate 2 Phase 2": int(sum(r.gate_2_phase_2 or 0 for r in count_rows)),
                "Gate 1": int(sum(r.gate_1 or 0 for r in count_rows)),
                "Has not undergone Gated process": int(sum(r.has_not_undergone_gated_process or 0 for r in count_rows)),
            }

        projects = sum(by_status.values())

        total_mw_row = next((r for r in mw_rows if (r.technology_type or "").upper() == "TOTAL"), None)
        if total_mw_row:
            total_mw = sum(
                filter(
                    None,
                    [
                        total_mw_row.gate_2_protected_26_27,
                        total_mw_row.gate_2_phase_1,
                        total_mw_row.gate_2_phase_2,
                        total_mw_row.gate_1,
                        total_mw_row.has_not_undergone_gated_process,
                    ],
                )
            )
        else:
            total_mw = sum(
                sum(
                    filter(
                        None,
                        [
                            r.gate_2_protected_26_27,
                            r.gate_2_phase_1,
                            r.gate_2_phase_2,
                            r.gate_1,
                            r.has_not_undergone_gated_process,
                        ],
                    )
                )
                for r in mw_rows
            )
    else:
        projects = len(records)
        total_mw = sum(r.mw or 0.0 for r in records)
        status_counter = Counter(r.status or "In Queue" for r in records)
        by_status = dict(status_counter)

    next_position = projects + 1
    return GspQueue(
        projects=projects,
        total_mw=round(total_mw, 2),
        by_status=by_status,
        next_position=next_position,
    )


MIN_CONFIDENCE_RECORDS = 3


def timescales(gsp_id: str | None, snap: Snapshot) -> Timescales | None:
    """Indicative connection timescales from past outcome records at the GSP."""
    if not gsp_id or not gsp_id.strip():
        return None

    target = _normalize_gsp(gsp_id)
    records = [
        r
        for r in snap.gsp_project_status
        if _normalize_gsp(r.gsp) == target or target in _normalize_gsp(r.gsp) or _normalize_gsp(r.gsp) in target
    ]
    if not records:
        return None

    durations: list[float] = []
    for r in records:
        if r.months is not None:
            durations.append(float(r.months))
        elif r.application_date:
            end_date = r.offer_date or r.energisation_date
            if end_date:
                m = (end_date - r.application_date).days / 30.4375
                durations.append(round(m, 1))

    if not durations:
        return None

    durations.sort()
    n = len(durations)
    low_confidence = n < MIN_CONFIDENCE_RECORDS

    if n == 1:
        p25 = durations[0]
        median = durations[0]
        p75 = durations[0]
    else:
        q = statistics.quantiles(durations, n=4)
        p25 = round(q[0], 1)
        median = round(statistics.median(durations), 1)
        p75 = round(q[2], 1)

    return Timescales(
        p25_months=p25,
        p75_months=p75,
        median_months=median,
        records=n,
        low_confidence=low_confidence,
    )
