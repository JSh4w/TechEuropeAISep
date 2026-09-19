"""Market revenue: per-duration revenue stack from named, sourced streams."""

from __future__ import annotations

from bessible.assumptions import ASSUMPTIONS_DIR, AssumptionSet


def load_market_assumptions() -> AssumptionSet:
    """Load `data/assumptions/market.json`."""
    return AssumptionSet.load(ASSUMPTIONS_DIR / "market.json")
