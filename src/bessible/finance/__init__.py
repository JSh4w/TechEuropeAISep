"""Financial model: cost, curtailment and returns, computed in plain code."""

from __future__ import annotations

from bessible.assumptions import ASSUMPTIONS_DIR, AssumptionSet


def load_finance_assumptions() -> AssumptionSet:
    """Load `data/assumptions/finance.json`."""
    return AssumptionSet.load(ASSUMPTIONS_DIR / "finance.json")
