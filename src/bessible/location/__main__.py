"""`uv run python -m bessible.location <lat> <lon> [--full]`: print the collated data for a coordinate as JSON.

Geometry is left out unless `--full` is given. The per-source outcome goes to stderr.
"""

from __future__ import annotations

import asyncio
import json
import sys

from . import Coordinates, collate

USAGE = "usage: python -m bessible.location <lat> <lon> [--full]"
N_COORDS = 2


def main() -> None:
    """Collate one coordinate and print it."""
    args = [a.strip(",") for a in sys.argv[1:] if a != "--full"]
    if len(args) != N_COORDS:
        sys.exit(USAGE)
    data = asyncio.run(collate(Coordinates(lat=float(args[0]), lon=float(args[1]))))
    for s in data.sources:
        records = "" if s.records is None else f" ({s.records})"
        sys.stderr.write(f"{s.status:8}{s.name}{records}{' - ' + s.detail if s.detail else ''}\n")
    full = "--full" in sys.argv
    sys.stdout.write(json.dumps(data.model_dump(mode="json") if full else data.without_geometry(), indent=2) + "\n")


if __name__ == "__main__":
    main()
