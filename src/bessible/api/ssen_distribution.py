"""SSEN Distribution open data portal - CKAN action API (same envelope as ``neso`` / ``nged``).

Portal: https://data.ssen.co.uk   API: https://data-api.ssen.co.uk/api/3/action/

SSEN Distribution is the DNO for CENTRAL SOUTHERN ENGLAND (SEPD: Wiltshire, Hampshire, Dorset, Berkshire,
Oxfordshire, west London) and the NORTH OF SCOTLAND (SHEPD). Not to be confused with ``ssen`` (SSEN
*Transmission*, a separate company portal). It is the counterpart of ``ukpn`` / ``nged`` for those areas.

Notes (verified live 2026-09):
- No key. Cloudflare answers HTTP 403 to default client User-Agents (curl, python-httpx): send a browser-like
  one (``HEADERS``).
- ``datastore_search_sql`` needs an account ("Authorization Error"), so as with NGED there is no spatial query:
  fetch the whole table (headroom 998 rows / 1.4 MB, ECR 1.3k rows / 3.8 MB) and use ``nearest()`` (section 4).
- Unknowns are the text "DATA NOT AVAILABLE" / "DATA NOT APPLICABLE" / "N/A" (or ""), even in numeric columns; all are
  read as None. Several numeric columns are text upstream ("10.38") and are coerced to float.
- Resource ids change when a new edition is published (headroom: roughly quarterly; ECR: monthly). If one 404s,
  take the newest CSV resource from ``PackageShowRequest(id=HEADROOM_PACKAGE | ECR_PACKAGE)``.
- The ECR here is "Part 1" (>= 1 MW).
- Overhead lines: one 437k-row table (98 MB) dominated by LV / 11 kV. ``lines_request()`` keeps 22-132 kV
  (``network_type`` "EHV" = 22/33/66 kV, "EHV+" = 132 kV): 14k rows, ~4 MB. Geometry is WKT text.
"""

from __future__ import annotations

from datetime import datetime
from typing import ClassVar

from pydantic import Field

from . import ckan, geo
from .base import NullMarkerResponse

BASE_URL = "https://data-api.ssen.co.uk/api/3/action/"

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; bessible/0.1; +https://data.ssen.co.uk)"}

HEADROOM_PACKAGE = "generation-availability-and-network-capacity"

HEADROOM_RESOURCE_ID = "52e9a305-ad90-4c81-9175-20a40ef57894"  # "Headroom Dashboard Data - March 2026"

ECR_PACKAGE = "embedded_capacity_register"

ECR_RESOURCE_ID = "bbae6797-364a-4b2d-a01a-8395e21bee76"  # "SSEN ECR Part 1 - 1MW September 2026 CSV"

LINES_PACKAGE = "ssen_overhead_lines"

LINES_RESOURCE_ID = "c6b53ab0-760b-4fbc-ae9c-996363815ee9"

# exact ``energy_source_1`` value for batteries, upstream typo included (``filters`` is exact-match only)
STORAGE_ENERGY_SOURCE = "STORED ENERGY (ALL STORED ENERGY IRRESPECTVE OF THE ORIGINAL ENERGY SOURCE)"


# ------------------------------------------ 1. Request ------------------------------------------ #


class DatastoreSearchRequest(ckan.DatastoreSearchRequest):
    """GET datastore_search on the SSEN Distribution portal (params as for NESO). Send ``HEADERS``."""

    URL: ClassVar[str] = BASE_URL + "datastore_search"


class PackageShowRequest(ckan.PackageShowRequest):
    """GET package_show on the SSEN Distribution portal, e.g. to find the current edition's resource id."""

    URL: ClassVar[str] = BASE_URL + "package_show"


# ----------------------------------------- 2. Response ------------------------------------------ #


class HeadroomResponse(ckan.CkanResponse):
    """Response of datastore_search on the Headroom Dashboard Data."""

    result: ckan.DatastoreSearchResult[HeadroomSite] | None = None


class EcrResponse(ckan.CkanResponse):
    """Response of datastore_search on the Embedded Capacity Register."""

    result: ckan.DatastoreSearchResult[EcrRecord] | None = None


class LinesResponse(ckan.CkanResponse):
    """Response of datastore_search on SSEN Overhead Lines."""

    result: ckan.DatastoreSearchResult[OverheadLine] | None = None


# ------------------------------------ 3. Response sub-models ------------------------------------ #


class _Record(NullMarkerResponse):
    """A datastore row with SSEN's "not available" markers read as None."""

    NULL_MARKERS: ClassVar[frozenset[str]] = frozenset({"", "N/A", "DATA NOT AVAILABLE", "DATA NOT APPLICABLE"})

    id: int | None = Field(default=None, alias="_id")


class HeadroomSite(_Record):
    """Row of the Headroom Dashboard Data: capacity per substation.

    The BESS-relevant numbers are ``estimated_generation_headroom_mw`` (export) and
    ``estimated_demand_headroom_mva`` (import), their RAG flags and the named constraint, plus any
    reinforcement already planned (works + completion date).
    """

    assetid: str | None = Field(default=None, alias="AssetID")
    gsp_grouping: str | None = Field(default=None, alias="gsp_grouping___default_order")
    licence_area: str | None = Field(default=None, alias="map___license_area")  # "England / SEPD" | "Scotland / SHEPD"
    substation: str | None = Field(default=None, alias="Substation")  # e.g. "Westbury Primary"
    upstream_gsp: str | None = Field(
        default=None, alias="Upstream GSP"
    )  # e.g. "Melksham GSP" (join to NESO after clean_site_name)
    upstream_bsp: str | None = Field(default=None, alias="Upstream BSP")
    substation_type: str | None = Field(default=None, alias="Substation Type")  # "Primary" | "BSP" | "GSP"
    voltage_kv: str | None = Field(default=None, alias="voltage__kv_")  # text, e.g. "33 / 11"
    lat: float | None = Field(default=None, alias="Location Latitude")
    lon: float | None = Field(default=None, alias="Location Longitude")
    grid_reference: str | None = Field(default=None, alias="Grid Reference")
    substation_comment: str | None = Field(default=None, alias="Substation Comment")
    ltds_cim_nodes: str | None = Field(default=None, alias="LTDS CIM Nodes")
    transformer_nameplate_ratings: str | None = Field(default=None, alias="Transformer Nameplate Ratings")
    single_transformer_site: str | None = Field(default=None, alias="Single Transformer Site")
    maximum_observed_gross_demand_mva: float | None = Field(default=None, alias="maximum_observed_gross_demand__mva_")
    minimum_observed_gross_demand_mva: float | None = Field(default=None, alias="minimum_observed_gross_demand__mva_")
    contracted_demand_excl_bess_mva: float | None = Field(default=None, alias="contracted_demand_excl_bess__mva_")
    contracted_bess_demand_mva: float | None = Field(
        default=None, alias="contracted_bess_demand__mva_"
    )  # batteries already contracted to import here
    estimated_demand_headroom_mva: float | None = Field(
        default=None, alias="estimated_demand_headroom__mva_"
    )  # import headroom
    substation_demand_rag_status: str | None = Field(default=None, alias="Substation Demand RAG Status")
    demand_constraint: str | None = Field(default=None, alias="Demand Constraint")
    tia_threshold: str | None = Field(
        default=None, alias="TIA Threshold"
    )  # above this size NESO must assess the transmission impact, e.g. "1MW"
    connected_generation_mw: float | None = Field(default=None, alias="connected_generation__mw_")
    contracted_generation_mw: float | None = Field(default=None, alias="contracted_generation__mw_")
    technical_limits_agreed_at_gsp: str | None = Field(
        default=None, alias="Technical Limits Agreed at GSP"
    )  # "Yes" = curtailable connections ahead of transmission works
    estimated_generation_headroom_mw: float | None = Field(
        default=None, alias="estimated_generation_headroom__mw_"
    )  # export headroom
    unsafe_3_phase_break_fault_rating_ka: float | None = Field(
        default=None, alias="unsafe_3_phase_break_fault_rating__ka_"
    )
    unsafe_3_phase_break_fault_level_ka: float | None = Field(
        default=None, alias="unsafe_3_phase_break_fault_level__ka_"
    )
    substation_generation_rag_status: str | None = Field(
        default=None, alias="Substation Generation RAG Status"
    )  # "Red" | "Amber" | "Green"
    generation_constraint: str | None = Field(
        default=None, alias="Generation Constraint"
    )  # e.g. "Upstream Thermal Capacity"
    upstream_reinforcement_works: str | None = Field(default=None, alias="Upstream Reinforcement Works")
    upstream_reinforcement_completion_date: str | None = Field(
        default=None, alias="Upstream Reinforcement Completion Date"
    )
    substation_reinforcement_works: str | None = Field(default=None, alias="Substation Reinforcement Works")
    substation_reinforcement_completion_date: str | None = Field(
        default=None, alias="Substation Reinforcement Completion Date"
    )


class EcrRecord(_Record):
    """Row of the Embedded Capacity Register, >= 1 MW (Ofgem-mandated columns, as ``ukpn.EmbeddedCapacityRecord``)."""

    export_mpan_msid: str | None = Field(default=None, alias="export_mpan___msid")  # mangled upstream ("2.00006E+12")
    import_mpan_msid: str | None = Field(default=None, alias="import_mpan___msid")
    customer_name: str | None = Field(default=None, alias="Customer Name")
    customer_site: str | None = Field(default=None, alias="Customer Site")
    address_line_1: str | None = Field(default=None, alias="Address Line 1")
    address_line_2: str | None = Field(default=None, alias="Address Line 2")
    town_city: str | None = Field(default=None, alias="town__city")
    county: str | None = Field(default=None, alias="County")
    postcode: str | None = Field(default=None, alias="Postcode")
    country: str | None = Field(default=None, alias="Country")
    eastings: str | None = Field(default=None, alias="location__x_coordinate___eastings__where_data_is_held_")
    northings: str | None = Field(default=None, alias="location__y_coordinate___northings__where_data_is_held_")
    grid_supply_point: str | None = Field(default=None, alias="Grid Supply Point")
    bulk_supply_point: str | None = Field(default=None, alias="Bulk Supply Point")
    primary: str | None = Field(default=None, alias="Primary")
    poc_voltage_kv: float | None = Field(default=None, alias="point_of_connection__poc__voltage__kv_")
    licence_area: str | None = Field(default=None, alias="Licence Area")
    energy_source_1: str | None = Field(
        default=None, alias="Energy Source 1"
    )  # upper case: "SOLAR", "STORED ENERGY", ...
    energy_conversion_technology_1: str | None = Field(default=None, alias="Energy Conversion Technology 1")
    chp_cogeneration_yes_no: str | None = Field(default=None, alias="chp_cogeneration__yes_no_")
    storage_capacity_1_mwh: str | None = Field(default=None, alias="storage_capacity_1__mwh_")
    storage_duration_1_hours: str | None = Field(default=None, alias="storage_duration_1__hours_")
    registered_capacity_1_mw: float | None = Field(
        default=None, alias="energy_source___energy_conversion_technology_1___registered_"
    )
    energy_source_2: str | None = Field(default=None, alias="Energy Source 2")
    energy_conversion_technology_2: str | None = Field(default=None, alias="Energy Conversion Technology 2")
    chp_cogeneration_2_yes_no: str | None = Field(default=None, alias="chp_cogeneration_2__yes_no_")
    storage_capacity_2_mwh: str | None = Field(default=None, alias="storage_capacity_2__mwh_")
    storage_duration_2_hours: str | None = Field(default=None, alias="storage_duration_2__hours_")
    registered_capacity_2_mw: float | None = Field(
        default=None, alias="energy_source___energy_conversion_technology_2___registered_"
    )
    energy_source_3: str | None = Field(default=None, alias="Energy Source 3")
    energy_conversion_technology_3: str | None = Field(default=None, alias="Energy Conversion Technology 3")
    chp_cogeneration_3_yes_no: str | None = Field(default=None, alias="chp_cogeneration_3__yes_no_")
    storage_capacity_3_mwh: str | None = Field(default=None, alias="storage_capacity_3__mwh_")
    storage_duration_3_hours: str | None = Field(default=None, alias="storage_duration_3__hours_")
    registered_capacity_3_mw: str | None = Field(
        default=None, alias="energy_source___energy_conversion_technology_3___registered_"
    )
    flexible_connection_yes_no: str | None = Field(default=None, alias="flexible_connection__yes_no_")
    connection_status: str | None = Field(
        default=None, alias="Connection Status"
    )  # "CONNECTED" | "ACCEPTED TO CONNECT"
    already_connected_registered_capacity_mw: float | None = Field(
        default=None, alias="already_connected_registered_capacity__mw_"
    )
    maximum_export_capacity_mw: float | None = Field(default=None, alias="maximum_export_capacity__mw_")
    maximum_export_capacity_mva: float | None = Field(default=None, alias="maximum_export_capacity__mva_")
    maximum_import_capacity_mw: float | None = Field(default=None, alias="maximum_import_capacity__mw_")
    maximum_import_capacity_mva: float | None = Field(default=None, alias="maximum_import_capacity__mva_")
    date_connected: str | None = Field(default=None, alias="Date Connected")  # text, "19/11/2024"
    accepted_to_connect_registered_capacity_mw: float | None = Field(
        default=None, alias="accepted_to_connect_registered_capacity__mw_"
    )
    change_to_maximum_export_capacity_mw: float | None = Field(
        default=None, alias="change_to_maximum_export_capacity__mw_"
    )
    change_to_maximum_export_capacity_mva: float | None = Field(
        default=None, alias="change_to_maximum_export_capacity__mva_"
    )
    change_to_maximum_import_capacity_mw: float | None = Field(
        default=None, alias="change_to_maximum_import_capacity__mw_"
    )
    change_to_maximum_import_capacity_mva: float | None = Field(
        default=None, alias="change_to_maximum_import_capacity__mva_"
    )
    date_accepted: str | None = Field(default=None, alias="Date Accepted")
    target_energisation_date: str | None = Field(default=None, alias="Target Energisation Date")
    distribution_service_provider_y_n: str | None = Field(default=None, alias="distribution_service_provider__y_n_")
    transmission_service_provider_y_n: str | None = Field(default=None, alias="transmission_service_provider__y_n_")
    reference: str | None = Field(default=None, alias="Reference")
    in_a_connection_queue_y_n: str | None = Field(default=None, alias="in_a_connection_queue__y_n_")
    distribution_reinforcement_reference: str | None = Field(default=None, alias="Distribution Reinforcement Reference")
    transmission_reinforcement_reference: str | None = Field(default=None, alias="Transmission Reinforcement Reference")
    last_updated: datetime | None = Field(default=None, alias="Last Updated")
    transmission_and_distribution_contracted_t_d: str | None = Field(
        default=None, alias="transmission_and_distribution_contracted__t_d_"
    )
    lat: float | None = Field(default=None, alias="Latitude")
    lon: float | None = Field(default=None, alias="Longitude")
    unique_id: str | None = Field(default=None, alias="Unique ID")  # e.g. "SSEN0663-1MW-CONNECTED"


class OverheadLine(_Record):
    """Row of SSEN Overhead Lines: one line section."""

    line_id: int | None = Field(default=None, alias="id")
    nominal_voltage_pp: str | None = None  # "33.000 kV", "132.000 kV", "11.000 kV", "230.000 V"
    circuit_id: int | None = None
    circuit_nrn: str | None = None  # network reference number, e.g. "6709.004.000.00"
    route: str | None = None  # WKT LINESTRING in EPSG:27700 (not requested by ``lines_request``)
    route_lat_long: str | None = None  # WKT LINESTRING, "lon lat" pairs in WGS84
    network_type: str | None = None  # "LV" | "HV" | "EHV" | "EHV+"


# -------------------- 4. Not from the API (helpers, registries, transforms) --------------------- #


def headroom_request() -> DatastoreSearchRequest:
    """Every primary, BSP and GSP with its headroom. Parse with ``HeadroomResponse``."""
    return DatastoreSearchRequest(resource_id=HEADROOM_RESOURCE_ID, limit=32000)


def ecr_request(*, storage_only: bool = False) -> DatastoreSearchRequest:
    """The whole embedded capacity register (>= 1 MW). Parse with ``EcrResponse``."""
    return DatastoreSearchRequest(
        resource_id=ECR_RESOURCE_ID,
        filters={"Energy Source 1": STORAGE_ENERGY_SOURCE} if storage_only else None,
        limit=32000,
    )


def lines_request() -> DatastoreSearchRequest:
    """Every overhead line of 22 kV and above, WGS84 geometry only. Parse with ``LinesResponse``."""
    return DatastoreSearchRequest(
        resource_id=LINES_RESOURCE_ID,
        filters={"network_type": ["EHV", "EHV+"]},
        fields=["_id", "id", "nominal_voltage_pp", "circuit_id", "circuit_nrn", "route_lat_long", "network_type"],
        limit=32000,
    )


def clean_site_name(name: str) -> str:
    """Strip the "GSP" / "BSP" / "Primary" suffix so a name matches NESO's "Connection Site"."""
    words = name.split()
    while words and words[-1].upper() in {"GSP", "BSP", "PRIMARY"}:
        words.pop()
    return " ".join(words)


def linestring_coordinates(wkt: str) -> list[list[float]]:
    """GeoJSON ``[lon, lat]`` coordinates of a WKT ``LINESTRING(lon lat,lon lat,...)``."""
    body = wkt[wkt.index("(") + 1 : wkt.rindex(")")]
    return [[float(v) for v in pair.split()[:2]] for pair in body.split(",")]


def position(record: HeadroomSite | EcrRecord) -> tuple[float | None, float | None]:
    """(lat, lon) of a row."""
    return record.lat, record.lon


def nearest[T: HeadroomSite | EcrRecord](
    records: list[T], lat: float, lon: float, max_km: float
) -> list[tuple[float, T]]:
    """(km, record) within `max_km` of a WGS84 point, nearest first. Stands in for a spatial query."""
    return geo.nearest(records, lat, lon, max_km, position)
