"""Load the committed UKPN capacity snapshot (``data/ukpn/``). No network, no key."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from functools import lru_cache
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from bessible.api import ukpn as ukpn_api
from bessible.config import settings
from bessible.ukpn.models import (
    GridSubstation,
    GspProjectStatusRecord,
    Table2aTransformerRecord,
    Table6InterestRecord,
)

if TYPE_CHECKING:
    from pathlib import Path

DATASET_ID = "ukpn-capacity-heatmap"
DATASET_URL = f"https://ukpowernetworks.opendatasoft.com/explore/dataset/{DATASET_ID}/"
GRID_DATASET_ID = "grid-and-primary-sites"
GRID_DATASET_URL = f"https://ukpowernetworks.opendatasoft.com/explore/dataset/{GRID_DATASET_ID}/"
GSP_DATASET_ID = "ukpn-gsp-project-status"
GSP_DATASET_URL = f"https://ukpowernetworks.opendatasoft.com/explore/dataset/{GSP_DATASET_ID}/"
TABLE6_DATASET_ID = "ltds-table-6-interest-connections"
TABLE6_DATASET_URL = f"https://ukpowernetworks.opendatasoft.com/explore/dataset/{TABLE6_DATASET_ID}/"
TABLE2A_DATASET_ID = "ukpn-ltds-table-2a-transformer-2w"
TABLE2A_DATASET_URL = f"https://ukpowernetworks.opendatasoft.com/explore/dataset/{TABLE2A_DATASET_ID}/"

HEATMAP_FILE = "heatmap.json"
GRID_SUBSTATIONS_FILE = "grid_substations.json"
GSP_PROJECT_STATUS_FILE = "gsp_project_status.json"
TABLE6_FILE = "table6.json"
TABLE2A_FILE = "table2a.json"
MANIFEST_FILE = "manifest.json"


class SnapshotNotFoundError(Exception):
    """No snapshot on disk. Retrying will not help."""


class Snapshot(BaseModel):
    """Primary and grid substations from UKPN datasets, plus provenance."""

    fetched_at: date
    partial: bool
    substations: list[ukpn_api.CapacityHeatmapSite]
    grid_substations: list[GridSubstation] = Field(default_factory=list)
    gsp_project_status: list[GspProjectStatusRecord] = Field(default_factory=list)
    table6_records: list[Table6InterestRecord] = Field(default_factory=list)
    table2a_records: list[Table2aTransformerRecord] = Field(default_factory=list)
    export_ceiling_validated: bool = False
    export_ceiling_failing_substations: list[str] = Field(default_factory=list)


def snapshot_age_days(snap: Snapshot, today: date | None = None) -> int:
    """Age of the snapshot in days relative to today."""
    curr = today or datetime.now(UTC).date()
    return (curr - snap.fetched_at).days


def _read_records[T: BaseModel](path: Path, model: type[T]) -> list[T]:
    if not path.exists():
        return []
    body = json.loads(path.read_text(encoding="utf-8"))
    items = body.get("results", body if isinstance(body, list) else [])
    return [model.model_validate(item) for item in items]


def load_snapshot(directory: Path | None = None) -> Snapshot:
    """Read and validate the snapshot. Keeps only rows with a name and coordinates."""
    root = directory or settings.data_dir / "ukpn"
    if not (root / HEATMAP_FILE).exists() or not (root / MANIFEST_FILE).exists():
        msg = f"No UKPN snapshot in {root}. Run `uv run python -m bessible.ukpn.ingest` (needs UKPN_API_KEY)."
        raise SnapshotNotFoundError(msg)
    manifest = json.loads((root / MANIFEST_FILE).read_text(encoding="utf-8"))
    body = ukpn_api.DATASETS["capacity_heatmap"].parse(json.loads((root / HEATMAP_FILE).read_text(encoding="utf-8")))
    rows = [r for r in body.results if r.name and r.latitude is not None and r.longitude is not None]

    grid_raw = _read_records(root / GRID_SUBSTATIONS_FILE, GridSubstation)
    grid_rows = [g for g in grid_raw if g.name and g.position]

    return Snapshot(
        fetched_at=date.fromisoformat(manifest["fetched_at"]),
        partial=bool(manifest.get("partial", False)),
        substations=rows,
        grid_substations=grid_rows,
        gsp_project_status=_read_records(root / GSP_PROJECT_STATUS_FILE, GspProjectStatusRecord),
        table6_records=_read_records(root / TABLE6_FILE, Table6InterestRecord),
        table2a_records=_read_records(root / TABLE2A_FILE, Table2aTransformerRecord),
        export_ceiling_validated=bool(manifest.get("export_ceiling_validated", False)),
        export_ceiling_failing_substations=list(manifest.get("export_ceiling_failing_substations", [])),
    )


@lru_cache(maxsize=1)
def get_snapshot() -> Snapshot:
    """Cached snapshot from the default directory."""
    return load_snapshot()
