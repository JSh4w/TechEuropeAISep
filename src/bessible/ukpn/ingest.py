"""Rebuild ``data/ukpn/`` from the live UKPN portal: ``uv run python -m bessible.ukpn.ingest`` (needs UKPN_API_KEY)."""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime

import httpx

from bessible.api import opendatasoft, ukpn
from bessible.config import settings
from bessible.ukpn.models import GridSubstation
from bessible.ukpn.snapshot import (
    DATASET_ID,
    GRID_DATASET_ID,
    GRID_SUBSTATIONS_FILE,
    HEATMAP_FILE,
    MANIFEST_FILE,
)

PAGE = 100
MAX_OFFSET = 10_000  # Opendatasoft: offset + limit <= 10000


def main() -> int:
    """Fetch heatmap and grid substation rows, validate them, then write the snapshot."""
    if settings.ukpn_api_key is None:
        sys.stderr.write("UKPN_API_KEY is not set (add it to .env).\n")
        return 1

    headers = opendatasoft.auth_headers(settings.ukpn_api_key.get_secret_value())

    # 1. Primary capacity heatmap
    h_spec = ukpn.DATASETS["capacity_heatmap"]
    heatmap_rows: list[dict[str, object]] = []
    with httpx.Client(timeout=30.0, headers=headers) as client:
        while len(heatmap_rows) < MAX_OFFSET:
            req = opendatasoft.RecordsRequest(
                dataset=h_spec.dataset, base_url=h_spec.base_url, limit=PAGE, offset=len(heatmap_rows), order_by="mrid"
            )
            resp = client.get(req.url(), params=req.params())
            resp.raise_for_status()
            body = resp.json()
            h_spec.parse(body)  # fail before writing anything if schema moved
            heatmap_rows.extend(body["results"])
            if len(heatmap_rows) >= body["total_count"] or not body["results"]:
                break

    # 2. Grid-level substations (132 kV)
    g_spec = ukpn.DATASETS["substations"]
    raw_grid_rows: list[dict[str, object]] = []
    with httpx.Client(timeout=30.0, headers=headers) as client:
        while len(raw_grid_rows) < MAX_OFFSET:
            req = opendatasoft.RecordsRequest(
                dataset=g_spec.dataset,
                base_url=g_spec.base_url,
                limit=PAGE,
                offset=len(raw_grid_rows),
                where="sitevoltage = 132 or sitetype = 'Grid Substation'",
                order_by="sitefunctionallocation",
            )
            resp = client.get(req.url(), params=req.params())
            resp.raise_for_status()
            body = resp.json()
            g_spec.parse(body)
            raw_grid_rows.extend(body["results"])
            if len(raw_grid_rows) >= body["total_count"] or not body["results"]:
                break

    # Validate into GridSubstation models
    validated_grid = [GridSubstation.model_validate(r) for r in raw_grid_rows]
    grid_data = [g.model_dump(mode="json") for g in validated_grid]

    out = settings.data_dir / "ukpn"
    out.mkdir(parents=True, exist_ok=True)
    (out / HEATMAP_FILE).write_text(json.dumps({"total_count": len(heatmap_rows), "results": heatmap_rows}))
    grid_payload = json.dumps({"total_count": len(grid_data), "results": grid_data}, indent=2)
    (out / GRID_SUBSTATIONS_FILE).write_text(grid_payload)

    manifest = {
        "fetched_at": datetime.now(UTC).date().isoformat(),
        "datasets": {
            DATASET_ID: {"rows": len(heatmap_rows), "file": HEATMAP_FILE},
            GRID_DATASET_ID: {"rows": len(grid_data), "file": GRID_SUBSTATIONS_FILE},
        },
        "partial": False,
    }
    (out / MANIFEST_FILE).write_text(json.dumps(manifest, indent=2))
    sys.stdout.write(f"Wrote {len(heatmap_rows)} heatmap rows and {len(grid_data)} grid substations to {out}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
