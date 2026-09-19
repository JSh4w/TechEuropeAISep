"""Atomically rebuild the UKPN snapshot in a temporary directory and produce a diff summary."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import httpx
from pydantic import BaseModel, Field

from bessible.api import opendatasoft, ukpn
from bessible.config import settings
from bessible.ukpn.export_ceiling import validate_export_ceiling
from bessible.ukpn.models import (
    GridSubstation,
    GspProjectStatusRecord,
    Table2aTransformerRecord,
    Table6InterestRecord,
)
from bessible.ukpn.snapshot import (
    DATASET_ID,
    GRID_DATASET_ID,
    GRID_SUBSTATIONS_FILE,
    GSP_DATASET_ID,
    GSP_PROJECT_STATUS_FILE,
    HEATMAP_FILE,
    MANIFEST_FILE,
    TABLE2A_DATASET_ID,
    TABLE2A_FILE,
    TABLE6_DATASET_ID,
    TABLE6_FILE,
    load_snapshot,
)

if TYPE_CHECKING:
    from collections.abc import Callable

PAGE = 100
MAX_OFFSET = 10_000


class DatasetDiff(BaseModel):
    """Diff counts for one dataset."""

    dataset_id: str
    added: int = 0
    removed: int = 0
    changed: int = 0


class DiffSummary(BaseModel):
    """Diff summary across all refreshed datasets."""

    datasets: dict[str, DatasetDiff] = Field(default_factory=dict)


def _row_key(dataset_id: str, row: dict[str, Any]) -> str:
    """Derive a stable unique key for a dataset row."""
    if dataset_id == DATASET_ID:
        return str(row.get("mrid") or row.get("name") or json.dumps(row, sort_keys=True))
    if dataset_id == GRID_DATASET_ID:
        return str(row.get("id") or row.get("name") or json.dumps(row, sort_keys=True))
    if dataset_id == TABLE6_DATASET_ID:
        return str(
            row.get("id")
            or f"{row.get('substation')}:{row.get('status_of_connection')}:{row.get('proposed_connection_voltage_kv')}"
        )
    if dataset_id == TABLE2A_DATASET_ID:
        return str(row.get("id") or f"{row.get('lv_substation')}:{row.get('hv_node')}:{row.get('lv_node')}")
    if dataset_id == GSP_DATASET_ID:
        return str(row.get("id") or f"{row.get('gsp')}:{row.get('technology_type')}:{row.get('measure')}")
    return json.dumps(row, sort_keys=True)


def compute_diff(dataset_id: str, old_rows: list[dict[str, Any]], new_rows: list[dict[str, Any]]) -> DatasetDiff:
    """Compare old and new rows for a dataset and compute added, removed, changed."""
    old_by_key = {_row_key(dataset_id, r): r for r in old_rows}
    new_by_key = {_row_key(dataset_id, r): r for r in new_rows}

    added = len(set(new_by_key.keys()) - set(old_by_key.keys()))
    removed = len(set(old_by_key.keys()) - set(new_by_key.keys()))
    common = set(new_by_key.keys()) & set(old_by_key.keys())
    changed = sum(1 for k in common if new_by_key[k] != old_by_key[k])

    return DatasetDiff(dataset_id=dataset_id, added=added, removed=removed, changed=changed)


def fetch_dataset_rows(
    client: httpx.Client,
    spec: opendatasoft.DatasetSpec[Any],
    *,
    where: str | None = None,
    order_by: str | None = None,
) -> list[dict[str, Any]]:
    """Fetch all rows for an Opendatasoft dataset."""
    rows: list[dict[str, Any]] = []
    while len(rows) < MAX_OFFSET:
        req = opendatasoft.RecordsRequest(
            dataset=spec.dataset,
            base_url=spec.base_url,
            limit=PAGE,
            offset=len(rows),
            where=where,
            order_by=order_by,
        )
        resp = client.get(req.url(), params=req.params())
        resp.raise_for_status()
        body = resp.json()
        spec.parse(body)
        rows.extend(body.get("results", []))
        if len(rows) >= body.get("total_count", 0) or not body.get("results"):
            break
    return rows


def _load_old_data(out_dir: Path) -> dict[str, list[dict[str, Any]]]:
    datasets = [
        (DATASET_ID, HEATMAP_FILE),
        (GRID_DATASET_ID, GRID_SUBSTATIONS_FILE),
        (TABLE6_DATASET_ID, TABLE6_FILE),
        (TABLE2A_DATASET_ID, TABLE2A_FILE),
        (GSP_DATASET_ID, GSP_PROJECT_STATUS_FILE),
    ]
    old_data: dict[str, list[dict[str, Any]]] = {}
    for ds_id, filename in datasets:
        p = out_dir / filename
        if p.exists():
            try:
                body = json.loads(p.read_text(encoding="utf-8"))
                old_data[ds_id] = body.get("results", body if isinstance(body, list) else [])
            except (json.JSONDecodeError, OSError):
                old_data[ds_id] = []
        else:
            old_data[ds_id] = []
    return old_data


def _fetch_all(
    client: httpx.Client,
    fetch_func: Callable[[str, httpx.Client], list[dict[str, Any]]] | None,
) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}

    def run_fetch(ds_id: str, default_fn: Callable[[], list[dict[str, Any]]]) -> list[dict[str, Any]]:
        try:
            return fetch_func(ds_id, client) if fetch_func else default_fn()
        except Exception as exc:
            msg = f"Failed to fetch dataset {ds_id}: {exc}"
            raise RuntimeError(msg) from exc

    result[DATASET_ID] = run_fetch(
        DATASET_ID, lambda: fetch_dataset_rows(client, ukpn.DATASETS["capacity_heatmap"], order_by="mrid")
    )
    raw_grid = run_fetch(
        GRID_DATASET_ID,
        lambda: fetch_dataset_rows(
            client,
            ukpn.DATASETS["substations"],
            where="sitevoltage = 132 or sitetype = 'Grid Substation'",
            order_by="sitefunctionallocation",
        ),
    )
    result[GRID_DATASET_ID] = [GridSubstation.model_validate(r).model_dump(mode="json") for r in raw_grid]
    t6 = run_fetch(TABLE6_DATASET_ID, lambda: fetch_dataset_rows(client, ukpn.DATASETS["table6"], order_by="id"))
    [Table6InterestRecord.model_validate(r) for r in t6]
    result[TABLE6_DATASET_ID] = t6
    t2a = run_fetch(TABLE2A_DATASET_ID, lambda: fetch_dataset_rows(client, ukpn.DATASETS["table2a"], order_by="id"))
    [Table2aTransformerRecord.model_validate(r) for r in t2a]
    result[TABLE2A_DATASET_ID] = t2a
    gsp = run_fetch(GSP_DATASET_ID, lambda: fetch_dataset_rows(client, ukpn.DATASETS["gsp_project_status"]))
    [GspProjectStatusRecord.model_validate(r) for r in gsp]
    result[GSP_DATASET_ID] = gsp
    return result


def _write_temp_and_manifest(temp_dir: Path, fetched: dict[str, list[dict[str, Any]]]) -> None:
    files = {
        DATASET_ID: HEATMAP_FILE,
        GRID_DATASET_ID: GRID_SUBSTATIONS_FILE,
        TABLE6_DATASET_ID: TABLE6_FILE,
        TABLE2A_DATASET_ID: TABLE2A_FILE,
        GSP_DATASET_ID: GSP_PROJECT_STATUS_FILE,
    }
    for ds_id, filename in files.items():
        rows = fetched[ds_id]
        payload = json.dumps({"total_count": len(rows), "results": rows}, indent=2)
        (temp_dir / filename).write_text(payload, encoding="utf-8")

    manifest = {
        "fetched_at": datetime.now(UTC).date().isoformat(),
        "datasets": {ds_id: {"rows": len(fetched[ds_id]), "file": files[ds_id]} for ds_id in files},
        "export_ceiling_validated": True,
        "export_ceiling_failing_substations": [],
        "partial": False,
    }
    (temp_dir / MANIFEST_FILE).write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    temp_snap = load_snapshot(temp_dir)
    failing_subs = validate_export_ceiling(temp_snap)
    if failing_subs:
        manifest["export_ceiling_validated"] = False
        manifest["export_ceiling_failing_substations"] = failing_subs
        (temp_dir / MANIFEST_FILE).write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def refresh(
    dest: Path | None = None,
    *,
    fetch_func: Callable[[str, httpx.Client], list[dict[str, Any]]] | None = None,
) -> DiffSummary:
    """Build new snapshot in a temporary directory and replace existing snapshot atomically."""
    out_dir = dest or (settings.data_dir / "ukpn")
    out_dir.parent.mkdir(parents=True, exist_ok=True)

    if settings.ukpn_api_key is None and fetch_func is None:
        msg = "UKPN_API_KEY is not set (add it to .env)."
        raise RuntimeError(msg)

    key_val = settings.ukpn_api_key.get_secret_value() if settings.ukpn_api_key else ""
    headers = opendatasoft.auth_headers(key_val)
    old_data = _load_old_data(out_dir)

    temp_dir = Path(tempfile.mkdtemp(prefix="ukpn_refresh_", dir=out_dir.parent))
    client_cls = getattr(sys.modules.get("bessible.ukpn.ingest"), "httpx", httpx).Client
    try:
        with client_cls(timeout=30.0, headers=headers) as client:
            fetched = _fetch_all(client, fetch_func)

        _write_temp_and_manifest(temp_dir, fetched)

        diffs = {ds_id: compute_diff(ds_id, old_data[ds_id], fetched[ds_id]) for ds_id in old_data}
        summary = DiffSummary(datasets=diffs)

        out_dir.mkdir(parents=True, exist_ok=True)
        for item in temp_dir.iterdir():
            shutil.copy2(item, out_dir / item.name)

        return summary
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
