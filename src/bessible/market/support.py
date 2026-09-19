"""Long-duration support streams (cap and floor, Ultra-LDES) for qualifying rows only."""

from __future__ import annotations

from datetime import date

from pydantic import HttpUrl

from bessible.assumptions import AssumptionSet
from bessible.models import StreamValue

SUPPORT_SCHEMES = {
    "cap_and_floor": ("Ofgem LDES cap and floor", "https://www.ofgem.gov.uk/"),
    "ultra_lds": ("Ultra-LDES support scheme", "https://www.ofgem.gov.uk/"),
}
RULE_KEYS = ("min_duration_h", "min_mw", "gbp_per_mw_year")


def _rules(name: str, a: AssumptionSet) -> dict[str, float]:
    rules = a.mapping(name)
    for key in RULE_KEYS:
        if key not in rules:
            from bessible.assumptions import MissingAssumption  # noqa: PLC0415

            raise MissingAssumption(f"{name}.{key}")
    return rules


def qualifying(duration_h: int, mw: float, a: AssumptionSet) -> list[str]:
    """Support streams whose rules this duration and capacity meet. Raises `MissingAssumption` for a missing rule."""
    names = []
    for name in SUPPORT_SCHEMES:
        rules = _rules(name, a)
        if duration_h >= rules["min_duration_h"] and mw >= rules["min_mw"]:
            names.append(name)
    return names


def support_stream(name: str, a: AssumptionSet) -> StreamValue:
    """Build the labelled support stream for a qualifying row."""
    scheme, url = SUPPORT_SCHEMES[name]
    entry = a.entry(name)
    return StreamValue(
        stream=name,
        gbp_per_mw_year=_rules(name, a)["gbp_per_mw_year"],
        source=entry.source,
        source_url=HttpUrl(url),
        as_of=date.fromisoformat(entry.date),
        cached=False,
        placeholder=entry.status == "placeholder",
        scheme=scheme,
    )
