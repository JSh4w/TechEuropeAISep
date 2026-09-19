"""SSEN Transmission open data portal (Opendatasoft Explore API v2.1, same request shape as ``ukpn``).

Portal: https://ssentransmission.opendatasoft.com  (69 datasets; the BESS-relevant ones are in DATASETS / REGISTERS)

SSEN Transmission (SHET) owns the TRANSMISSION network in the NORTH OF SCOTLAND only (substations span
lat 55.6-58.5). It is not the southern-England distribution network (SSEN Distribution, data.ssen.co.uk),
so points in England return no records.

Notes (verified live 2026-09):
- Auth, paging and errors: see ``opendatasoft`` (``auth_headers(key)``, ``limit`` <= 100, ``OdsError``).
- Substations and lines come as two datasets each: "grid" (132 kV) and "supergrid" (275/400 kV).
- ``voltage`` is in volts (132000), not kV.
- The two registers are SSEN's slice of NESO's TEC / Embedded registers (same columns, prefixed
  ``tec_register_records_``). They have no coordinates: match ``connection_site`` by name.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import Field

from .base import ApiResponse
from .opendatasoft import DatasetSpec, GeoPoint, GeoShape, RecordsRequest, RecordsResponse

BASE_URL = "https://ssentransmission.opendatasoft.com/api/explore/v2.1"

STORAGE_PLANT_TYPE = "Energy Storage System"  # also appears inside hybrids, e.g. "Energy Storage System;Wind Onshore"


# ------------------------------------------ 1. Request ------------------------------------------ #

# `opendatasoft.RecordsRequest` with `base_url=BASE_URL`; build one with `DATASETS[name].near(...)` or
# `register_request(...)` (section 4).


# ----------------------------------------- 2. Response ------------------------------------------ #

# `opendatasoft.RecordsResponse[<row model>]`; each dataset's row model is in section 3.


# ------------------------------------ 3. Response sub-models ------------------------------------ #


class SubstationSite(ApiResponse):
    """Row of ``ssen-transmission-substation-site-grid`` / ``-supergrid``: one substation compound."""

    name: str | None = None  # e.g. "ARDKINGLAS SUBSTATION"
    voltage: int | None = None  # volts
    ex_date: str | None = None  # export date, "30/01/2026"
    geo_shape: GeoShape | None = None  # site polygon
    geo_point_2d: GeoPoint | None = None  # centroid


class OverheadLine(ApiResponse):
    """Row of ``overhead-line-grid`` / ``ssen-transmission-overhead-line-supergrid``: one line segment."""

    voltage: int | None = None  # volts
    ex_date: str | None = None
    geo_shape: GeoShape | None = None  # LineString (3D coordinates)
    geo_point_2d: GeoPoint | None = None  # segment midpoint


class RegisterRecord(ApiResponse):
    """Row of the SSEN TEC register or Embedded register (columns as NESO's ``TecRegisterRecord``)."""

    project_name: str | None = Field(None, alias="tec_register_records_project_name")
    customer_name: str | None = Field(None, alias="tec_register_records_customer_name")
    connection_site: str | None = Field(None, alias="tec_register_records_connection_site")  # only location column
    stage: int | None = Field(None, alias="tec_register_records_stage")
    mw_connected: float | None = Field(None, alias="tec_register_records_mw_connected")
    mw_increase_decrease: float | None = Field(None, alias="tec_register_records_mw_increase_decrease")
    cumulative_total_capacity_mw: float | None = Field(None, alias="tec_register_records_cumulative_total_capacity_mw")
    mw_effective_from: date | None = Field(None, alias="tec_register_records_mw_effective_from")
    project_status: str | None = Field(None, alias="tec_register_records_project_status")
    agreement_type: str | None = Field(None, alias="tec_register_records_agreement_type")
    host_to: str | None = Field(None, alias="tec_register_records_host_to")  # always SHET here
    plant_type: str | None = Field(None, alias="tec_register_records_plant_type")
    project_id: str | None = Field(None, alias="tec_register_records_project_id")
    project_number: str | None = Field(None, alias="tec_register_records_project_number")


# -------------------- 4. Not from the API (helpers, registries, transforms) --------------------- #


def _geo(dataset: str, response: type[RecordsResponse[Any]]) -> DatasetSpec[Any]:
    return DatasetSpec(BASE_URL, dataset, "geo_shape", response, "geo_point_2d")


DATASETS: dict[str, DatasetSpec[Any]] = {
    "substations_132kv": _geo("ssen-transmission-substation-site-grid", RecordsResponse[SubstationSite]),
    "substations_supergrid": _geo("ssen-transmission-substation-site-supergrid", RecordsResponse[SubstationSite]),
    "overhead_lines_132kv": _geo("overhead-line-grid", RecordsResponse[OverheadLine]),
    "overhead_lines_supergrid": _geo("ssen-transmission-overhead-line-supergrid", RecordsResponse[OverheadLine]),
}


"""Geo datasets: ``DATASETS["substations_132kv"].near(lat, lon, metres)``."""


REGISTERS: dict[str, str] = {
    "tec_register": "ssen-transmission-tec-transmission-entry-capacity-register",
    "embedded_register": "ssen-transmission-embedded-register",
}


def register_request(register: str, site: str | None = None, *, storage_only: bool = False) -> RecordsRequest:
    """Query a register for projects at a connection site (word match on the name), largest first.

    `site` is a substation name with or without its suffix, e.g. "BLACKHILLOCK SUBSTATION" -> "blackhillock".
    """
    where = []
    if site:
        word = site.upper().removesuffix(" SUBSTATION").replace('"', "")
        where.append(f'search(tec_register_records_connection_site, "{word}")')
    if storage_only:
        where.append(f'search(tec_register_records_plant_type, "{STORAGE_PLANT_TYPE}")')
    return RecordsRequest(
        dataset=REGISTERS[register],
        where=" and ".join(where) or None,
        order_by="tec_register_records_cumulative_total_capacity_mw desc",
        limit=100,
        base_url=BASE_URL,
    )


def parse_register(body: dict[str, Any]) -> RecordsResponse[RegisterRecord]:
    """Validate a register records body."""
    return RecordsResponse[RegisterRecord].model_validate(body)
