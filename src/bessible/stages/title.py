"""Title boundary lookup stage placeholder."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from bessible.models import Artifact, TitleInput, TitleOutput

DEFAULT_TITLE_NUMBER = "BK123456"
DEFAULT_AREA_M2 = 25000.0
COORD_DELTA = 0.002


def _write_boundary_file(run_id: str, file_name: str, geojson: dict[str, Any]) -> None:
    run_dir = Path(f"out/{run_id}")
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / file_name).write_text(json.dumps(geojson, indent=2), encoding="utf-8")


async def find_title_boundaries(inp: TitleInput) -> TitleOutput:
    """Look up HM Land Registry title boundary and cadastral polygon."""
    pos = inp.location.position
    geojson: dict[str, Any] = {
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [
                    [pos.lon - COORD_DELTA, pos.lat - COORD_DELTA],
                    [pos.lon + COORD_DELTA, pos.lat - COORD_DELTA],
                    [pos.lon + COORD_DELTA, pos.lat + COORD_DELTA],
                    [pos.lon - COORD_DELTA, pos.lat + COORD_DELTA],
                    [pos.lon - COORD_DELTA, pos.lat - COORD_DELTA],
                ]
            ],
        },
        "properties": {
            "title_number": DEFAULT_TITLE_NUMBER,
            "area_m2": DEFAULT_AREA_M2,
        },
    }

    file_name = "boundary.geojson"
    await asyncio.to_thread(_write_boundary_file, inp.run_id, file_name, geojson)

    art = Artifact(
        id=f"title-{inp.run_id[:8]}",
        stage="title",
        claim=f"HM Land Registry title {DEFAULT_TITLE_NUMBER} boundary confirmed covering {DEFAULT_AREA_M2:,.0f} m²",
        file_path=file_name,
        confidence=0.96,
        model_used="dummy",
    )

    return TitleOutput(
        title_number=DEFAULT_TITLE_NUMBER,
        boundary_geojson=geojson,
        area_m2=DEFAULT_AREA_M2,
        artifacts=[art],
    )
