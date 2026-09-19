"""Load the committed UKPN capacity snapshot (``data/ukpn/``). No network, no key."""

from __future__ import annotations

import json
from datetime import date
from functools import lru_cache
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from bessible.api import ukpn as ukpn_api
from bessible.config import settings
from bessible.ukpn.models import GridSubstation

if TYPE_CHECKING:
    from pathlib import Path

DATASET_ID = "ukpn-capacity-heatmap"
DATASET_URL = f"https://ukpowernetworks.opendatasoft.com/explore/dataset/{DATASET_ID}/"
GRID_DATASET_ID = "grid-and-primary-sites"
GRID_DATASET_URL = f"https://ukpowernetworks.opendatasoft.com/explore/dataset/{GRID_DATASET_ID}/"
HEATMAP_FILE = "heatmap.json"
GRID_SUBSTATIONS_FILE = "grid_substations.json"
MANIFEST_FILE = "manifest.json"


class SnapshotNotFoundError(Exception):
    """No snapshot on disk. Retrying will not help."""


class Snapshot(BaseModel):
    """Primary and grid substations from UKPN datasets, plus provenance."""

    fetched_at: date
    partial: bool
    substations: list[ukpn_api.CapacityHeatmapSite]
    grid_substations: list[GridSubstation] = Field(default_factory=list)


def load_snapshot(directory: Path | None = None) -> Snapshot:
    """Read and validate the snapshot. Keeps only rows with a name and coordinates."""
    root = directory or settings.data_dir / "ukpn"
    if not (root / HEATMAP_FILE).exists() or not (root / MANIFEST_FILE).exists():
        msg = f"No UKPN snapshot in {root}. Run `uv run python -m bessible.ukpn.ingest` (needs UKPN_API_KEY)."
        raise SnapshotNotFoundError(msg)
    manifest = json.loads((root / MANIFEST_FILE).read_text())
    body = ukpn_api.DATASETS["capacity_heatmap"].parse(json.loads((root / HEATMAP_FILE).read_text()))
    rows = [r for r in body.results if r.name and r.latitude is not None and r.longitude is not None]

    grid_rows: list[GridSubstation] = []
    grid_path = root / GRID_SUBSTATIONS_FILE
    if grid_path.exists():
        grid_body = json.loads(grid_path.read_text())
        raw_items = grid_body.get("results", grid_body if isinstance(grid_body, list) else [])
        for item in raw_items:
            grid_sub = GridSubstation.model_validate(item)
            if grid_sub.name and grid_sub.position:
                grid_rows.append(grid_sub)

    return Snapshot(
        fetched_at=date.fromisoformat(manifest["fetched_at"]),
        partial=bool(manifest.get("partial", False)),
        substations=rows,
        grid_substations=grid_rows,
    )


@lru_cache(maxsize=1)
def get_snapshot() -> Snapshot:
    """Cached snapshot from the default directory."""
    return load_snapshot()
