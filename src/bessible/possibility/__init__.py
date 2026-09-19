"""Can a battery be built here at all? `assess(Proposal) -> PossibilityReport`.

    from bessible.location import Coordinates, collate
    from bessible.possibility import Proposal, assess

    location = await collate(Coordinates(lat=51.11, lon=-2.99))
    report = assess(Proposal(location=location, battery_mw=20))
    report.possible, report.blockers, report.caveats, report.unknowns

`hard` holds the deterministic checks, each a plain `Proposal -> Check` function listed in `HARD_CHECKS`.
`uv run python -m bessible.possibility <lat> <lon> [mw] [hours]` runs them on a live location.
"""

from __future__ import annotations

from .hard import HARD_CHECKS, assess
from .models import Check, Limits, PossibilityReport, Proposal

__all__ = ["HARD_CHECKS", "Check", "Limits", "PossibilityReport", "Proposal", "assess"]
