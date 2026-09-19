"""Load and ingest DESNZ Renewable Energy Planning Database (REPD) battery storage records."""

from __future__ import annotations

import argparse
import json
import logging
import math
import sys
from datetime import UTC, date, datetime
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field, HttpUrl

from bessible.config import settings
from bessible.models import NearbyProject, Position

log = logging.getLogger(__name__)

EARTH_RADIUS_KM = 6371.0


def haversine_km(a: Position, lat: float, lon: float) -> float:
    """Great-circle distance in km from `a` to a WGS84 point."""
    p1, p2 = math.radians(a.lat), math.radians(lat)
    dphi, dlmb = p2 - p1, math.radians(lon - a.lon)
    h = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(h))


DATASET_NAME = "desnz-repd"
DATASET_URL = (
    "https://www.gov.uk/government/publications/renewable-energy-planning-database-monthly-extract"
)
REPD_FILE = "repd.json"
MANIFEST_FILE = "manifest.json"


class RepdProject(BaseModel):
    """Raw or validated REPD project record."""

    id: str
    name: str
    mw: float
    status: str
    status_date: date
    latitude: float
    longitude: float
    postcode: str | None = None
    technology_type: str = "Battery"


class RepdSnapshot(BaseModel):
    """Committed snapshot of REPD projects."""

    fetched_at: date
    dataset: str = DATASET_NAME
    dataset_url: HttpUrl = HttpUrl(DATASET_URL)
    records_count: int = 0
    projects: list[RepdProject] = Field(default_factory=list)
    partial: bool = False
    note: str | None = None


# Alias for compatibility with design.md interface
Snapshot = RepdSnapshot


class RepdSnapshotNotFoundError(Exception):
    """No REPD snapshot found on disk."""


def load_repd_snapshot(directory: Path | None = None) -> RepdSnapshot:
    """Load and validate the committed REPD snapshot from data/repd/."""
    root = directory or (settings.data_dir / "repd")
    data_path = root / REPD_FILE
    manifest_path = root / MANIFEST_FILE

    if not data_path.exists() or not manifest_path.exists():
        msg = f"No REPD snapshot in {root}. Run `uv run python -m bessible.planning.ingest_repd`."
        raise RepdSnapshotNotFoundError(msg)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    raw_data = json.loads(data_path.read_text(encoding="utf-8"))
    results = raw_data.get("results", raw_data if isinstance(raw_data, list) else [])

    projects: list[RepdProject] = []
    for item in results:
        try:
            projects.append(RepdProject.model_validate(item))
        except Exception:
            log.warning("Skipping invalid REPD item %s", item, exc_info=True)

    fetched_at_raw = manifest.get("fetched_at")
    fetched_at = date.fromisoformat(fetched_at_raw) if fetched_at_raw else datetime.now(UTC).date()

    return RepdSnapshot(
        fetched_at=fetched_at,
        dataset=manifest.get("dataset", DATASET_NAME),
        dataset_url=HttpUrl(manifest.get("dataset_url", DATASET_URL)),
        records_count=len(projects),
        projects=projects,
        partial=bool(manifest.get("partial", False)),
        note=manifest.get("note"),
    )


@lru_cache(maxsize=1)
def get_repd_snapshot() -> RepdSnapshot:
    """Cached snapshot from default data directory."""
    return load_repd_snapshot()


def nearby_batteries(
    pos: Position,
    snap: RepdSnapshot | None = None,
    radius_km: float = 5.0,
) -> list[NearbyProject]:
    """Find battery storage projects within radius_km of position from REPD snapshot."""
    if snap is None:
        try:
            snap = get_repd_snapshot()
        except RepdSnapshotNotFoundError:
            log.warning("REPD snapshot not found; returning empty nearby list")
            return []

    nearby: list[NearbyProject] = []
    for project in snap.projects:
        dist = haversine_km(pos, project.latitude, project.longitude)
        if dist <= radius_km:
            nearby.append(
                NearbyProject(
                    id=project.id,
                    name=project.name,
                    mw=project.mw,
                    status=project.status,
                    status_date=project.status_date,
                    distance_km=round(dist, 2),
                )
            )

    nearby.sort(key=lambda p: p.distance_km)
    return nearby


def ingest_from_records(
    records: list[dict[str, object]],
    out_dir: Path,
    *,
    partial: bool = False,
    note: str | None = None,
) -> int:
    """Validate records and write snapshot files."""
    validated = [RepdProject.model_validate(r) for r in records]
    out_dir.mkdir(parents=True, exist_ok=True)

    dumped = [p.model_dump(mode="json") for p in validated]
    (out_dir / REPD_FILE).write_text(
        json.dumps({"total_count": len(dumped), "results": dumped}, indent=2),
        encoding="utf-8",
    )

    manifest = {
        "fetched_at": datetime.now(UTC).date().isoformat(),
        "dataset": DATASET_NAME,
        "dataset_url": DATASET_URL,
        "records_count": len(dumped),
        "file": REPD_FILE,
        "partial": partial,
        "note": note or "REPD snapshot written by ingest_repd",
    }
    (out_dir / MANIFEST_FILE).write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    sys.stdout.write(f"Wrote {len(dumped)} REPD records to {out_dir}\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Ingest command-line entrypoint."""
    parser = argparse.ArgumentParser(description="Ingest REPD battery data into data/repd/")
    parser.add_argument("--file", type=Path, help="Path to local REPD JSON or CSV file")
    parser.add_argument("--out", type=Path, default=settings.data_dir / "repd", help="Output directory")
    args = parser.parse_args(argv)

    out_dir: Path = args.out
    if args.file and args.file.exists():
        data = json.loads(args.file.read_text(encoding="utf-8"))
        results = data.get("results", data if isinstance(data, list) else [])
        return ingest_from_records(results, out_dir, partial=False)

    # If no file provided, verify existing or reload
    try:
        snap = load_repd_snapshot(out_dir)
    except RepdSnapshotNotFoundError:
        sys.stderr.write("No existing snapshot found and no input file provided.\n")
        return 1
    else:
        sys.stdout.write(f"Existing snapshot loaded with {len(snap.projects)} projects.\n")
        return 0


if __name__ == "__main__":
    sys.exit(main())
