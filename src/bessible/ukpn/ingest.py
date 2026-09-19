"""Rebuild ``data/ukpn/`` from the live UKPN portal: ``uv run python -m bessible.ukpn.ingest`` (needs UKPN_API_KEY)."""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime

import httpx

from bessible.api import opendatasoft, ukpn
from bessible.config import settings
from bessible.ukpn.snapshot import DATASET_ID, HEATMAP_FILE, MANIFEST_FILE

PAGE = 100
MAX_OFFSET = 10_000  # Opendatasoft: offset + limit <= 10000


def main() -> int:
    """Fetch every heatmap row, validate it, then write the snapshot. An existing snapshot stays if anything fails."""
    if settings.ukpn_api_key is None:
        sys.stderr.write("UKPN_API_KEY is not set (add it to .env).\n")
        return 1
    spec = ukpn.DATASETS["capacity_heatmap"]
    headers = opendatasoft.auth_headers(settings.ukpn_api_key.get_secret_value())
    rows: list[dict[str, object]] = []
    with httpx.Client(timeout=30.0, headers=headers) as client:
        while len(rows) < MAX_OFFSET:
            req = opendatasoft.RecordsRequest(
                dataset=spec.dataset, base_url=spec.base_url, limit=PAGE, offset=len(rows), order_by="mrid"
            )
            resp = client.get(req.url(), params=req.params())
            resp.raise_for_status()
            body = resp.json()
            spec.parse(body)  # fail before writing anything if the schema moved
            rows.extend(body["results"])
            if len(rows) >= body["total_count"] or not body["results"]:
                break
    out = settings.data_dir / "ukpn"
    out.mkdir(parents=True, exist_ok=True)
    (out / HEATMAP_FILE).write_text(json.dumps({"total_count": len(rows), "results": rows}))
    manifest = {
        "fetched_at": datetime.now(UTC).date().isoformat(),
        "datasets": {DATASET_ID: {"rows": len(rows), "file": HEATMAP_FILE}},
        "partial": False,
    }
    (out / MANIFEST_FILE).write_text(json.dumps(manifest, indent=2))
    sys.stdout.write(f"Wrote {len(rows)} rows to {out}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
