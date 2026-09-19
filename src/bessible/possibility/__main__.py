"""`uv run python -m bessible.possibility <lat> <lon> [mw=20] [hours=4] [--json]`: hard checks on a live location."""

from __future__ import annotations

import asyncio
import sys

from bessible.location import Coordinates, collate

from . import Proposal, assess

USAGE = "usage: python -m bessible.possibility <lat> <lon> [mw=20] [hours=4] [--json]"
MIN_ARGS = 2
MARKS = {"pass": "PASS", "warn": "WARN", "fail": "FAIL", "unknown": " ?  "}


def main() -> None:
    """Collate one coordinate, run the hard checks and print them."""
    args = [a.strip(",") for a in sys.argv[1:] if a != "--json"]
    if len(args) < MIN_ARGS:
        sys.exit(USAGE)
    lat, lon, mw, hours = (*map(float, args), 20.0, 4.0)[:4] if len(args) == MIN_ARGS else (*map(float, args), 4.0)[:4]
    location = asyncio.run(collate(Coordinates(lat=lat, lon=lon)))
    report = assess(Proposal.model_validate({"location": location, "battery_mw": mw, "duration_h": int(hours)}))
    if "--json" in sys.argv:
        sys.stdout.write(report.model_dump_json(indent=2) + "\n")
        return
    for check in report.checks:
        sys.stdout.write(f"{MARKS[check.outcome]}  {check.name:30} {check.reason}\n")
    sys.stdout.write(f"\n{'POSSIBLE' if report.possible else 'BLOCKED'}: {mw:g} MW / {hours:g} h at {lat}, {lon}\n")


if __name__ == "__main__":
    main()
