"""Load the committed UKPN capacity snapshot (``data/ukpn/``). No network, no key."""

from __future__ import annotations

import json
from datetime import date
from functools import lru_cache
from typing import TYPE_CHECKING

from pydantic import BaseModel

from bessible.api import ukpn as ukpn_api
from bessible.config import settings

if TYPE_CHECKING:
    from pathlib import Path

DATASET_ID = "ukpn-capacity-heatmap"
DATASET_URL = f"https://ukpowernetworks.opendatasoft.com/explore/dataset/{DATASET_ID}/"
HEATMAP_FILE = "heatmap.json"
MANIFEST_FILE = "manifest.json"


class SnapshotNotFoundError(Exception):
    """No snapshot on disk. Retrying will not help."""


class Snapshot(BaseModel):
    """Primary substations from the LTDS capacity heatmap, plus provenance."""

    fetched_at: date
    partial: bool
    substations: list[ukpn_api.CapacityHeatmapSite]


def load_snapshot(directory: Path | None = None) -> Snapshot:
    """Read and validate the snapshot. Keeps only rows with a name and coordinates."""
    root = directory or settings.data_dir / "ukpn"
    if not (root / HEATMAP_FILE).exists() or not (root / MANIFEST_FILE).exists():
        msg = f"No UKPN snapshot in {root}. Run `uv run python -m bessible.ukpn.ingest` (needs UKPN_API_KEY)."
        raise SnapshotNotFoundError(msg)
    manifest = json.loads((root / MANIFEST_FILE).read_text())
    body = ukpn_api.DATASETS["capacity_heatmap"].parse(json.loads((root / HEATMAP_FILE).read_text()))
    rows = [r for r in body.results if r.name and r.latitude is not None and r.longitude is not None]
    return Snapshot(
        fetched_at=date.fromisoformat(manifest["fetched_at"]),
        partial=bool(manifest.get("partial", False)),
        substations=rows,
    )


@lru_cache(maxsize=1)
def get_snapshot() -> Snapshot:
    """Cached snapshot from the default directory."""
    return load_snapshot()
