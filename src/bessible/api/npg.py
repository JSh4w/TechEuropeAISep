"""Northern Powergrid (NPg) open data portal (Opendatasoft Explore API v2.1).

Portal: https://northernpowergrid.opendatasoft.com
API: https://northernpowergrid.opendatasoft.com/api/explore/v2.1

Northern Powergrid is the DNO for the North East (NPgN) and Yorkshire (NPgY). It is the counterpart of ``ukpn``,
``nged``, ``ssen_distribution`` and ``sp_energy`` for these licence areas.

Notes (verified live 2026-09):
- Records queries take an API key in the header: ``Authorization: Apikey <key>`` (see ``auth_headers``); the key
  raises the anonymous rate limit. Free registration at https://northernpowergrid.opendatasoft.com.
- ``ltds-capacity-heatmap`` follows the LTDS Capacity Heatmap information model (the same fields as UKPN's), with the
  geo field ``latlon``. ``gsp`` / ``bsp`` are NPg asset ids ("GSP-000038"), not site names.
- Paging and limits: standard ODS Explore API v2.1, max 100 rows per request (see ``opendatasoft``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .base import ApiResponse
from .opendatasoft import DatasetSpec, GeoPoint, RecordsResponse

if TYPE_CHECKING:
    from typing import Any

BASE_URL = "https://northernpowergrid.opendatasoft.com/api/explore/v2.1"


def auth_headers(api_key: str) -> dict[str, str]:
    """Request headers carrying the portal API key."""
    return {"Authorization": f"Apikey {api_key}"}


# ------------------------------------------ 1. Request ------------------------------------------ #

# `opendatasoft.RecordsRequest` with `base_url=BASE_URL`; build one via `DATASETS[name].near(...)`.


# ----------------------------------------- 2. Response ------------------------------------------ #

# `opendatasoft.RecordsResponse[<row model>]`; row models defined below.


# ------------------------------------ 3. Response sub-models ------------------------------------ #


class CapacityHeatmapSite(ApiResponse):
    """Row of ``ltds-capacity-heatmap``: LTDS headroom per substation, in MW.

    ``generationavailablecapacity`` is export headroom, ``demandavailablecapacity`` import headroom. The constraint
    fields hold "Green" | "Amber" | "Red"; the limiting-factor fields repeat the colour ("Red - Fault Level").
    """

    mrid: str | None = None  # NPg asset id, e.g. "PSP-000009"
    name: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    latlon: GeoPoint | None = None
    type: str | None = None  # "Primary" | "BSP" | "GSP"
    voltages: float | None = None  # kV of the busbar the figures describe
    gsp: str | None = None  # asset id, not a name
    bsp: str | None = None  # asset id, not a name
    area: str | None = None  # "NPgN" | "NPgY"
    odp_primary_name: str | None = None
    demandfirmcapacity: float | None = None
    generationfirmcapacity: float | None = None
    reversepowerflowtotalcapacity: float | None = None
    reversepowerflowavailablecapacity: float | None = None
    demandminimum: float | None = None
    demandmaximum: float | None = None
    generationcontractedcapacity: float | None = None
    demandcontractedcapacity: float | None = None
    generationavailablecapacity: float | None = None
    demandavailablecapacity: float | None = None
    generationconstraint: str | None = None
    demandconstraint: str | None = None
    generationconstraintlimitingfactor: str | None = None
    demandconstraintlimitingfactor: str | None = None
    pastconnectionactivity: list[str] | None = None  # key:value fragments, e.g. '"voltage":11'


# ----------------------------------------- 4. Datasets ------------------------------------------ #

DATASETS: dict[str, DatasetSpec[Any]] = {
    "capacity_heatmap": DatasetSpec(
        BASE_URL, "ltds-capacity-heatmap", "latlon", RecordsResponse[CapacityHeatmapSite]
    ),
}
