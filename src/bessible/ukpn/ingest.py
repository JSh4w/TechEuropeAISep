"""Rebuild ``data/ukpn/`` from the live UKPN portal: ``uv run python -m bessible.ukpn.ingest`` (needs UKPN_API_KEY)."""

from __future__ import annotations

import argparse
import sys
from typing import TYPE_CHECKING

import httpx  # ruff: ignore[unused-import]

from bessible.config import settings
from bessible.ukpn.refresh import refresh

if TYPE_CHECKING:
    from bessible.ukpn.refresh import DiffSummary


def print_diff_summary(diff_summary: DiffSummary) -> None:
    """Format and print added, removed, and changed counts per dataset."""
    sys.stdout.write("\nDataset Diff Summary:\n")
    sys.stdout.write(f"  {'Dataset':<36} {'Added':<10} {'Removed':<10} {'Changed':<10}\n")
    sys.stdout.write("  " + "-" * 66 + "\n")
    for ds_id, diff in diff_summary.datasets.items():
        sys.stdout.write(f"  {ds_id:<36} {diff.added:<10} {diff.removed:<10} {diff.changed:<10}\n")
    sys.stdout.write("\n")


def build_parser() -> argparse.ArgumentParser:
    """Construct argument parser for UKPN snapshot ingestion."""
    parser = argparse.ArgumentParser(prog="bessible.ukpn.ingest", description="UKPN data snapshot ingest and refresh")
    parser.add_argument("--refresh", action="store_true", help="Atomically rebuild snapshot and print diff summary")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Fetch datasets, validate them, and update snapshot."""
    parser = build_parser()
    _ = parser.parse_known_args(argv if argv is not None else sys.argv[1:] if __name__ == "__main__" else [])

    if settings.ukpn_api_key is None:
        sys.stderr.write("UKPN_API_KEY is not set (add it to .env).\n")
        return 1

    try:
        sys.stdout.write("Refreshing UKPN snapshot atomically...\n")
        diff = refresh()
        print_diff_summary(diff)
        sys.stdout.write("Snapshot refreshed successfully.\n")
    except (RuntimeError, OSError, ValueError) as exc:
        sys.stderr.write(f"Ingest/refresh failed: {exc}\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
