"""National Grid Electricity Distribution (NGED) Connected Data portal - CKAN action API.

Portal: https://connecteddata.nationalgrid.co.uk  (same CKAN envelope as ``neso``)

NGED is the DNO for the SOUTH WEST, SOUTH WALES, EAST MIDLANDS and WEST MIDLANDS. It is the counterpart
of ``ukpn`` for those areas: headroom per substation and the embedded capacity register.

Notes (verified live 2026-09):
- Auth: header ``Authorization: <token>`` with no scheme word (see ``auth_headers``). Reads also work
  anonymously today, but the portal terms ask for the token.
- ``datastore_search_sql`` is DISABLED ("Action name not known"), and ``datastore_search`` only has exact-match
  ``filters`` and full-text ``q``. So there is no spatial query: fetch the whole (small) table once and pick
  the nearest rows client-side with ``nearest()`` (section 4). Primary + BSP rows: 1.2k, 1.4 MB. ECR: 7.2k rows, 19 MB
  in full, so project it with ``ECR_FIELDS``.
- Empty cells are ``""`` even in numeric-looking columns; they are read as None.
- The ECR resource is republished monthly under a new id ("ECR AUG 2026"): if ``ECR_RESOURCE_ID`` 404s, take the
  newest CSV resource from ``PackageShowRequest(id=ECR_PACKAGE)``.
- Overhead lines and 132/33 kV substation footprints are shapefile downloads only (no datastore).
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import ClassVar

from pydantic import Field

from . import ckan, geo
from .base import NullMarkerResponse

BASE_URL = "https://connecteddata.nationalgrid.co.uk/api/3/action/"

CAPACITY_MAP_PACKAGE = "nged-network-capacity"

CAPACITY_MAP_RESOURCE_ID = "d1895bd3-d9d2-4886-a0a3-b7eadd9ab6c2"  # 121k rows, all but 1.2k are "Secondary"

ECR_PACKAGE = "embedded-capacity-register"

ECR_RESOURCE_ID = "82a4ae83-77a3-4e7b-9060-8072ed96de9d"  # "ECR AUG 2026"; changes monthly

# exact ``energy_source_1`` value for batteries (``filters`` is exact-match only)
STORAGE_ENERGY_SOURCE = "Stored Energy (all stored energy irrespective of the original energy source)"


# ------------------------------------------ 1. Request ------------------------------------------ #


class DatastoreSearchRequest(ckan.DatastoreSearchRequest):
    """GET datastore_search on the NGED portal (params as for NESO)."""

    URL: ClassVar[str] = BASE_URL + "datastore_search"


class PackageShowRequest(ckan.PackageShowRequest):
    """GET package_show on the NGED portal, e.g. to find this month's ECR resource id."""

    URL: ClassVar[str] = BASE_URL + "package_show"


# ----------------------------------------- 2. Response ------------------------------------------ #


class CapacityMapResponse(ckan.CkanResponse):
    """Response of datastore_search on the Network Capacity Map."""

    result: ckan.DatastoreSearchResult[CapacityMapSite] | None = None


class EcrResponse(ckan.CkanResponse):
    """Response of datastore_search on the Embedded Capacity Register."""

    result: ckan.DatastoreSearchResult[EcrRecord] | None = None


# ------------------------------------ 3. Response sub-models ------------------------------------ #


class _Record(NullMarkerResponse):
    """A datastore row: NGED writes empty cells as ``""`` whatever the column type (read as None)."""

    id: int | None = Field(None, alias="_id")


class CapacityMapSite(_Record):
    """Row of the Network Capacity Map: headroom per substation, MW.

    The BESS-relevant numbers are ``generation_contracted_headroom_mw`` (export) and
    ``demand_contracted_headroom_mw`` (import) with their RAG flags. Most other columns are empty upstream
    (typed ``float | str`` because the datastore calls them text).
    """

    substation_id: int | None = Field(None, alias="substationID")
    heatmap_dataset_id: str | None = Field(None, alias="heatmapDatasetID")
    type: str | None = None  # "Primary" | "BSP" | "Secondary" (~120k distribution substations)
    area: str | None = None  # "South West" | "South Wales" | "East Midlands" | "West Midlands"
    name: str | None = None
    substation_number: int | None = Field(None, alias="substationNumber")
    description: str | None = None
    voltages: str | None = None
    longitude: float | None = None
    latitude: float | None = None
    primary: str | None = None
    bsp: str | None = Field(None, alias="BSP")  # bulk supply point feeding it, e.g. "Fraddon Bsp"
    gsp: str | None = Field(
        None, alias="GSP"
    )  # grid supply point, e.g. "Indian Queens  S.G.P." (join to NESO after clean_site_name)
    demand_total_capacity: float | str | None = Field(None, alias="demandTotalCapacity")
    demand_connected_headroom_mw: float | None = Field(
        None, alias="demandConnectedHeadroomMW"
    )  # import headroom against what is connected today
    demand_contracted_headroom_mw: float | None = Field(
        None, alias="demandContractedHeadroomMW"
    )  # ... after accepted-not-yet-connected schemes: the number that matters
    demand_quoted_capacity: float | str | None = Field(None, alias="demandQuotedCapacity")
    demand_available_capacity: float | str | None = Field(None, alias="demandAvailableCapacity")
    demand_maximum: float | str | None = Field(None, alias="demandMaximum")
    demand_minimum: float | str | None = Field(None, alias="demandMinimum")
    demand99_percentile: float | str | None = Field(None, alias="demand99Percentile")
    demand75_percentile: float | str | None = Field(None, alias="demand75Percentile")
    demand50_percentile: float | str | None = Field(None, alias="demand50Percentile")
    demand25_percentile: float | str | None = Field(None, alias="demand25Percentile")
    demand_connected_rag: str | None = Field(None, alias="demandConnectedRAG")
    demand_contracted_rag: str | None = Field(None, alias="demandContractedRAG")
    demand_constraint_limiting_factor: float | str | None = Field(None, alias="demandConstraintLimitingFactor")
    generation_total_capacity: float | str | None = Field(None, alias="generationTotalCapacity")
    generation_connected_headroom_mw: float | None = Field(None, alias="generationConnectedHeadroomMW")
    generation_contracted_headroom_mw: float | None = Field(None, alias="generationContractedHeadroomMW")
    generation_quoted_capacity: float | None = Field(None, alias="generationQuotedCapacity")
    generation_available_capacity: float | str | None = Field(None, alias="generationAvailableCapacity")
    generation_connected_rag: str | None = Field(
        None, alias="generationConnectedRAG"
    )  # "red" | "amber" | "green" (lower case)
    generation_contracted_rag: str | None = Field(None, alias="generationContractedRAG")
    generation_constraint_limiting_factor: float | str | None = Field(None, alias="generationConstraintLimitingFactor")
    breaker_rated_current: float | str | None = Field(None, alias="breakerRatedCurrent")
    breaker_breaking_capacity: float | str | None = Field(None, alias="breakerBreakingCapacity")
    breaker_making_capacity: float | str | None = Field(None, alias="breakerMakingCapacity")
    breaker_available_capacity: float | str | None = Field(None, alias="breakerAvailableCapacity")
    breaker_short_circuit_current: float | str | None = Field(None, alias="breakerShortCircuitCurrent")
    breaker_short_circuit_duration: float | str | None = Field(None, alias="breakerShortCircuitDuration")
    reverse_power_flow_total_capacity: float | str | None = Field(None, alias="reversePowerFlowTotalCapacity")
    reverse_power_flow_available_capacity: float | str | None = Field(None, alias="reversePowerFlowAvailableCapacity")


class EcrRecord(_Record):
    """Row of the Embedded Capacity Register (Ofgem-mandated columns, as ``ukpn.EmbeddedCapacityRecord``).

    Unlike UKPN's, this one lists sites below 1 MW too. Unknowns are the text "data not available".
    """

    export_mpan_msid: str | None = Field(None, alias="export_mpan/msid")
    import_mpan_msid: str | None = Field(None, alias="import_mpan/msid")
    customer_name: str | None = None
    customer_site: str | None = None
    address_line_1: str | None = None
    address_line_2: str | None = None
    town_city: str | None = Field(None, alias="Town/City")
    county: str | None = None
    postcode: str | None = None
    country: str | None = None
    eastings: str | None = Field(None, alias="location(x-coordinate):_eastings_(where_data_is_held)")
    northings: str | None = Field(None, alias="location(y-coordinate):_northings_(where_data_is_held)")
    grid_supply_point: str | None = None  # e.g. "Walpole 132Kv S Stn"
    bulk_supply_point: str | None = None
    primary: str | None = None
    poc_voltage_kv: str | None = Field(None, alias="point_of_connection(poc)_voltage(kv)")
    licence_area: str | None = None
    energy_source_1: str | None = (
        None  # "Solar", "Stored Energy (all stored energy ...)"; unused slots are "data not applicable"
    )
    energy_conversion_technology_1: str | None = Field(None, alias="Energy Conversion Technology 1")
    chp_cogeneration_yes_no: str | None = Field(None, alias="chp_cogeneration(yes/no)")
    storage_capacity_1_mwh: str | None = Field(None, alias="storage_capacity_1(mwh)")
    storage_duration_1_hours: str | None = Field(None, alias="storage_duration_1(hours)")
    registered_capacity_1_mw: float | None = Field(None, alias="energy_source_&_conversion_tech_1_reg_capacity_mw")
    energy_source_2: str | None = None
    energy_conversion_technology_2: str | None = Field(None, alias="Energy Conversion Technology 2")
    chp_cogeneration2_yes_no: str | None = Field(None, alias="chp_cogeneration2(yes/no)")
    storage_capacity_2_mwh: str | None = Field(None, alias="storage_capacity_2(mwh)")
    storage_duration_2_hours: str | None = Field(None, alias="storage_duration_2(hours)")
    registered_capacity_2_mw: float | None = Field(None, alias="energy_source_&_conversion_tech_2_reg_capacity_mw")
    energy_source_3: str | None = None
    energy_conversion_technology_3: str | None = Field(None, alias="Energy Conversion Technology 3")
    chp_cogeneration3_yes_no: str | None = Field(None, alias="chp_cogeneration3(yes/no)")
    storage_capacity_3_mwh: str | None = Field(None, alias="storage_capacity_3(mwh)")
    storage_duration_3_hours: str | None = Field(None, alias="storage_duration_3(hours)")
    registered_capacity_3_mw: float | None = Field(None, alias="energy_source_&_conversion_tech_3_reg_capacity_mw")
    flexible_connection_yes_no: str | None = Field(None, alias="flexible_connection (Yes/No)")
    connection_status: str | None = None  # "Connected" | "Accepted to connect"
    already_connected_registered_capacity_mw: float | None = Field(
        None, alias="already_connected_registered_capacity(mw)"
    )
    connected_maximum_export_capacity_mw: float | None = Field(None, alias="connected_maximum_export_capacity(mw)")
    connected_maximum_export_capacity_mva: float | None = Field(None, alias="connected_maximum_export_capacity(mva)")
    connected_maximum_import_capacity_mw: float | None = Field(None, alias="connected_maximum_import_capacity(mw)")
    connected_maximum_import_capacity_mva: float | None = Field(None, alias="connected_maximum_import_capacity(mva)")
    date_connected: datetime | None = None
    accepted_to_connect_registered_capacity_mw: str | None = Field(
        None, alias="accepted_to_connect_registered_capacity(mw)"
    )
    accepted_change_to_maximum_export_capacity_mw: str | None = Field(
        None, alias="accepted_change_to_maximum_export_capacity(mw)"
    )
    accepted_change_to_maximum_export_capacity_mva: str | None = Field(
        None, alias="accepted_change_to_maximum_export_capacity(mva)"
    )
    accepted_change_to_maximum_import_capacity_mw: str | None = Field(
        None, alias="accepted_change_to_maximum_import_capacity(mw)"
    )
    accepted_change_to_maximum_import_capacity_mva: str | None = Field(
        None, alias="accepted_change_to_maximum_import_capacity(mva)"
    )
    date_accepted: str | None = None  # text upstream, "06/03/2013 00:00"
    target_energisation_date: str | None = None  # text upstream, "30/12/2026"
    distribution_service_provider_y_n: str | None = Field(None, alias="distribution_service_provider(y/n)")
    transmission_service_provider_y_n: str | None = Field(None, alias="transmission_service_provider(y/n)")
    reference: str | None = None
    in_a_connection_queue_y_n: str | None = Field(None, alias="in_a_connection_queue(y/n)")
    distribution_reinforcement_reference: str | None = None
    transmission_reinforcement_reference: str | None = None
    last_updated: datetime | None = None
    lon: float | None = None
    lat: float | None = None  # null on ~16% of rows
    local_authority: str | None = None


# -------------------- 4. Not from the API (helpers, registries, transforms) --------------------- #


def auth_headers(api_key: str) -> dict[str, str]:
    """Request headers carrying the portal API token."""
    return {"Authorization": api_key}


def capacity_map_request() -> DatastoreSearchRequest:
    """Every primary and bulk supply point with its headroom. Parse with ``CapacityMapResponse``."""
    return DatastoreSearchRequest(
        resource_id=CAPACITY_MAP_RESOURCE_ID, filters={"type": ["Primary", "BSP"]}, limit=32000
    )


ECR_FIELDS = [
    "_id",
    "customer_site",
    "grid_supply_point",
    "bulk_supply_point",
    "primary",
    "energy_source_1",
    "Energy Conversion Technology 1",
    "storage_capacity_1(mwh)",
    "energy_source_&_conversion_tech_1_reg_capacity_mw",
    "connection_status",
    "already_connected_registered_capacity(mw)",
    "accepted_to_connect_registered_capacity(mw)",
    "date_connected",
    "target_energisation_date",
    "lon",
    "lat",
    "local_authority",
]


"""The ECR columns the assessment uses; the full table is 19 MB."""


def ecr_request(fields: list[str] | None = ECR_FIELDS, *, storage_only: bool = False) -> DatastoreSearchRequest:
    """The whole embedded capacity register (``fields=None`` for every column). Parse with ``EcrResponse``."""
    return DatastoreSearchRequest(
        resource_id=ECR_RESOURCE_ID,
        fields=fields,
        filters={"energy_source_1": STORAGE_ENERGY_SOURCE} if storage_only else None,
        limit=32000,
    )


def position(record: CapacityMapSite | EcrRecord) -> tuple[float | None, float | None]:
    """(lat, lon) of a row, whichever pair of column names it uses."""
    if isinstance(record, CapacityMapSite):
        return record.latitude, record.longitude
    return record.lat, record.lon


def nearest[T: CapacityMapSite | EcrRecord](
    records: list[T], lat: float, lon: float, max_km: float
) -> list[tuple[float, T]]:
    """(km, record) within `max_km` of a WGS84 point, nearest first. Stands in for a spatial query."""
    return geo.nearest(records, lat, lon, max_km, position)


def clean_site_name(name: str) -> str:
    """Strip NGED's suffixes so a GSP name matches NESO's "Connection Site".

    "Indian Queens  S.G.P." -> "Indian Queens"; "Walpole 132Kv S Stn" -> "Walpole".
    """
    name = re.sub(
        r"\b(S\.?G\.?P\.?|G\.?S\.?P\.?|B\.?S\.?P\.?|S Stn|\d+(/\d+)?\s?Kv)\b\.?", " ", name, flags=re.IGNORECASE
    )
    return " ".join(name.split())
