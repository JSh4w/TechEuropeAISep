"""SP Energy Networks (SPEN) open data portal (Opendatasoft Explore API v2.1).

Portal: https://spenergynetworks.opendatasoft.com
API: https://spenergynetworks.opendatasoft.com/api/explore/v2.1

SP Energy Networks is the DNO for:
- CENTRAL AND SOUTHERN SCOTLAND: SP Distribution plc (SPD), covering Glasgow, Edinburgh,
  Ayrshire, Dumfries & Galloway, Fife, and Borders.
- MERSEYSIDE, CHESHIRE, NORTH WALES AND NORTH SHROPSHIRE: SP Manweb plc (SPM).
- Transmission network in Central and Southern Scotland: SP Transmission plc (SPT).

It is the counterpart of ``ukpn``, ``nged``, and ``ssen_distribution`` for these licence areas.

Notes (verified live 2026-09):
- Datasets have "domain" visibility on the portal; records queries require an API key in the header:
  ``Authorization: Apikey <key>`` (see ``auth_headers``). Free registration at
  https://spenergynetworks.opendatasoft.com.
- Paging and limits: standard ODS Explore API v2.1, max 100 rows per request (see ``opendatasoft``).
- Errors: HTTP 400 with ``{"error_code": ..., "message": ...}`` -> ``OdsError``.
- Spatial queries: datasets use ``coordinates`` or ``geo_point_2d`` / ``geo_shape`` fields, enabling
  native ODSQL spatial filtering via ``within_distance(...)``.
"""

from __future__ import annotations

import re
from datetime import date
from typing import TYPE_CHECKING, ClassVar

from pydantic import Field

if TYPE_CHECKING:
    from typing import Any

from .base import ApiResponse, NullMarkerResponse
from .opendatasoft import DatasetSpec, GeoPoint, GeoShape, RecordsResponse

BASE_URL = "https://spenergynetworks.opendatasoft.com/api/explore/v2.1"

# Value of ``energy_source_1`` in the ECR for battery projects
STORAGE_ENERGY_SOURCE = "Stored Energy"

_MIN_SITE_NAME_LEN = 3
_GSP_CLEAN_RE = re.compile(
    r"\s*(?:gsp|sgp|bulk\s+supply\s+point|bsp|132\s*kv|33\s*kv|substation|\btee\b|[0-9]+kv).*$",
    re.IGNORECASE,
)


def auth_headers(api_key: str) -> dict[str, str]:
    """Request headers carrying the portal API key."""
    return {"Authorization": f"Apikey {api_key}"}


def clean_site_name(name: str) -> str:
    """Strip SPEN's suffixes so a GSP name matches NESO's "Connection Site"."""
    cleaned = _GSP_CLEAN_RE.sub("", name).strip()
    return cleaned if len(cleaned) >= _MIN_SITE_NAME_LEN else name.strip()


# ------------------------------------------ 1. Request ------------------------------------------ #

# `opendatasoft.RecordsRequest` with `base_url=BASE_URL`; build one via `DATASETS[name].near(...)`.


# ----------------------------------------- 2. Response ------------------------------------------ #

# `opendatasoft.RecordsResponse[<row model>]`; row models defined below.


# ------------------------------------ 3. Response sub-models ------------------------------------ #


class _Record(NullMarkerResponse):
    """A row with SPEN null markers ("", "-", "N/A", "DATA NOT AVAILABLE") mapped to None."""

    NULL_MARKERS: ClassVar[frozenset[str]] = frozenset({
        "",
        "-",
        "N/A",
        "NONE",
        "DATA NOT AVAILABLE",
        "DATA NOT APPLICABLE",
    })


class CapacityHeatmapSite(_Record):
    """Row of ``distribution-capacity-heatmaps-spd`` or ``distribution-capacity-heatmaps-spm``.

    Standard ENA Capacity Heatmap model showing spare MW import and export headroom,
    connection voltage, constraint flags (GREEN, AMBER, RED), and connection pipeline activity.
    """

    name: str | None = None
    site_name: str | None = None
    type: str | None = None  # Primary | BSP | Grid
    area: str | None = None  # SPD | SPM
    voltage: str | None = None
    demandfirmcapacity: float | None = None
    mgrid: str | None = None
    longitude: float | None = None
    latitude: float | None = None
    lat: float | None = None
    lon: float | None = None
    latitude_longitude: str | None = None
    gsp: str | None = None
    bsp: str | None = None
    grid_supply_point: str | None = None
    primary_substation: str | None = None
    proposed_connection_voltage_kv: float | None = None
    connection_voltage_kv: float | None = None
    demandmaximum: float | None = None
    demandminimum: float | None = None
    demandavailablecapacity: float | None = None
    demandconstraint: str | None = None  # GREEN | AMBER | RED
    demandconstraintlimitingfactor: str | None = None
    generationfirmcapacity: float | str | None = None
    generationavailablecapacity: float | str | None = None
    reversepowerflowtotalcapacity: float | str | None = None
    reversepowerflowavailablecapacity: float | str | None = None
    otherconstraints: str | None = None
    generationconstraint: str | None = None  # GREEN | AMBER | RED
    generationconstraintlimitingfactor: str | None = None
    past_connection_activity_total_demand_capacity: float | None = None
    past_connection_activity_total_generation_capacity: float | None = None
    past_connection_activity_total_demand_volume: int | None = None
    past_connection_activity_total_generation_volume: int | None = None
    group_132kv: str | None = Field(default=None, alias="132kv_group")
    group_33kv: str | None = Field(default=None, alias="33kv_group")
    hv_group_or_substation: str | None = None
    loadbudgetestimatesprovidedcount: float | None = None
    loadbudgetestimatesprovidedcapacity: float | None = None
    generationbudgetestimatesprovidedcount: float | None = None
    generationbudgetestimatesprovidedcapacity: float | None = None
    loadconnectionoffersmadecount: float | None = None
    loadconnectionoffersmadecapacity: float | None = None
    generationconnectionoffermadecount: float | None = None
    generationconnectionoffermadecapacity: float | None = None
    loadconnectionoffersacceptedcount: float | None = None
    loadconnectionoffersacceptedcapacity: float | None = None
    generationconnectionofferacceptedcount: float | None = None
    generationconnectionofferacceptedcapacity: float | None = None
    coordinates: GeoPoint | None = None

    @property
    def effective_name(self) -> str:
        """Preferred substation name."""
        return (self.site_name or self.name or "Unnamed").strip()

    @property
    def effective_lat(self) -> float | None:
        """Latitude from GeoPoint or scalar fields."""
        if self.coordinates and self.coordinates.lat is not None:
            return self.coordinates.lat
        return self.lat if self.lat is not None else self.latitude

    @property
    def effective_lon(self) -> float | None:
        """Longitude from GeoPoint or scalar fields."""
        if self.coordinates and self.coordinates.lon is not None:
            return self.coordinates.lon
        return self.lon if self.lon is not None else self.longitude

    @property
    def effective_voltage_kv(self) -> float | None:
        """Connection voltage in kV."""
        if self.proposed_connection_voltage_kv is not None:
            return self.proposed_connection_voltage_kv
        return self.connection_voltage_kv

    @property
    def effective_gsp(self) -> str | None:
        """Grid supply point name."""
        return self.gsp or self.grid_supply_point


class EmbeddedCapacityRecord(_Record):
    """Row of ``embedded-capacity-register``: connected and accepted generation and storage >= 1 MW.

    Ofgem-mandated register across all GB network operators.
    """

    export_mpan_msid: str | None = None
    import_mpan_msid: str | None = None
    customer_name: str | None = None
    customer_site: str | None = None  # project name
    address_line_1: str | None = None
    address_line_2: str | None = None
    town_city: str | None = None
    county: str | None = None
    postcode: str | None = None
    country: str | None = None
    eastings: str | None = Field(default=None, alias="location_xcoordinate_eastings_where_data_is_held")
    northings: str | None = Field(default=None, alias="location_ycoordinate_northings_where_data_is_held")
    grid_supply_point: str | None = None
    bulk_supply_point: str | None = None
    primary: str | None = None
    poc_voltage_kv: float | str | None = Field(default=None, alias="point_of_connection_poc_voltage_kv")
    licence_area: str | None = None  # SPD | SPM
    energy_source_1: str | None = None  # e.g. "Stored Energy", "Solar"
    energy_conversion_technology_1: str | None = None  # e.g. "Storage (Battery)"
    chp_cogeneration_yes_no: str | None = None
    storage_capacity_1_mwh: float | str | None = None
    storage_duration_1_hours: float | str | None = None
    registered_capacity_1_mw: float | str | None = Field(
        default=None, alias="energy_source_energy_conversion_technology_1_registered_capacity_mw"
    )
    energy_source_2: str | None = None
    energy_conversion_technology_2: str | None = None
    chp_cogeneration_2_yes_no: str | None = None
    storage_capacity_2_mwh: float | str | None = None
    storage_duration_2_hours: float | str | None = None
    registered_capacity_2_mw: float | str | None = Field(
        default=None, alias="energy_source_energy_conversion_technology_2_registered_capacity_mw"
    )
    energy_source_3: str | None = None
    energy_conversion_technology_3: str | None = None
    chp_cogeneration_3_yes_no: str | None = None
    storage_capacity_3_mwh: float | str | None = None
    storage_duration_3_hours: float | str | None = None
    registered_capacity_3_mw: float | str | None = Field(
        default=None, alias="energy_source_energy_conversion_technology_3_registered_capacity_mw"
    )
    flexible_connection_yes_no: str | None = None
    connection_status: str | None = None  # "Connected" | "Accepted to Connect"
    already_connected_registered_capacity_mw: float | str | None = None
    maximum_export_capacity_mw: float | str | None = None
    maximum_export_capacity_mva: float | str | None = None
    maximum_import_capacity_mw: float | str | None = None
    maximum_import_capacity_mva: float | str | None = None
    date_connected: date | str | None = None
    accepted_to_connect_registered_capacity_mw: float | str | None = None
    change_to_maximum_export_capacity_mw: float | str | None = None
    change_to_maximum_export_capacity_mva: float | str | None = None
    change_to_maximum_import_capacity_mw: float | str | None = None
    change_to_maximum_import_capacity_mva: float | str | None = None
    date_accepted: date | str | None = None
    target_energisation_date: date | str | None = None
    distribution_service_provider_y_n: str | None = None
    transmission_service_provider_y_n: str | None = None
    reference: str | None = None
    in_a_connection_queue_y_n: str | None = None
    distribution_reinforcement_reference: str | None = None
    transmission_reinforcement_reference: str | None = None
    last_updated: date | str | None = None
    query_disconnection: str | None = None
    unique_id: str | None = None
    coordinates: GeoPoint | None = None


class GisPointAsset(ApiResponse):
    """Row of ``spd_spt_gis_shapefiles_point_assets`` or ``spm_gis_shapefiles_point_assets``: substation point."""

    geo_point_2d: GeoPoint | None = None
    geo_shape: GeoShape | None = None
    sp_enid: int | None = None
    sub_name: str | None = None
    status: str | None = None
    lic_area: str | None = None
    sub_note: str | None = None
    asset_type: str | None = None
    voltage: float | str | None = None
    localauth: str | None = None


class GisLineAsset(ApiResponse):
    """Row of ``spd_spt_gis_shapefiles_line_assets`` or ``spm_gis_shapefiles_line_assets``: overhead line."""

    geo_point_2d: GeoPoint | None = None
    geo_shape: GeoShape | None = None
    sp_enid: int | None = None
    voltage: float | str | None = None
    status: str | None = None
    lic_area: str | None = None
    asset_type: str | None = None
    localauth: str | None = None


class TransmissionHeatMapRecord(ApiResponse):
    """Row of ``transmission-generation-heat-map0``: transmission generation projects."""

    projectid: str | None = None
    projectname: str | None = None
    connectionsite: str | None = None
    mwconnected: float | None = None
    mw_increasedecrease: float | None = None
    cumulativetotalcapacity_mw: float | None = None
    mweffectivefrom: date | str | None = None
    projectstatus: str | None = None
    planttype: str | None = None
    planttype_category: str | None = None
    coordinates: GeoPoint | None = None
    connection_year: str | None = None
    longitude: str | None = None
    latitude: str | None = None


class GspQueueRecord(ApiResponse):
    """Row of ``gsp-queue-position``: Single Digital View project pipeline."""

    unique_id: str | None = None
    export_capacity_mw: float | str | None = None
    license_area: str | None = None
    gsp_name: str | None = None
    generator_type: str | None = None


# -------------------- 4. Not from the API (helpers, registries, transforms) --------------------- #


DATASETS: dict[str, DatasetSpec[Any]] = {
    "capacity_heatmap_spd": DatasetSpec(
        BASE_URL, "distribution-capacity-heatmaps-spd", "coordinates", RecordsResponse[CapacityHeatmapSite]
    ),
    "capacity_heatmap_spm": DatasetSpec(
        BASE_URL, "distribution-capacity-heatmaps-spm", "coordinates", RecordsResponse[CapacityHeatmapSite]
    ),
    "embedded_capacity_register": DatasetSpec(
        BASE_URL, "embedded-capacity-register", "coordinates", RecordsResponse[EmbeddedCapacityRecord]
    ),
    "lines_spd": DatasetSpec(
        BASE_URL, "spd_spt_gis_shapefiles_line_assets", "geo_shape", RecordsResponse[GisLineAsset], "geo_point_2d"
    ),
    "lines_spm": DatasetSpec(
        BASE_URL, "spm_gis_shapefiles_line_assets", "geo_shape", RecordsResponse[GisLineAsset], "geo_point_2d"
    ),
    "substations_spd": DatasetSpec(
        BASE_URL, "spd_spt_gis_shapefiles_point_assets", "geo_point_2d", RecordsResponse[GisPointAsset]
    ),
    "substations_spm": DatasetSpec(
        BASE_URL, "spm_gis_shapefiles_point_assets", "geo_point_2d", RecordsResponse[GisPointAsset]
    ),
    "transmission_generation": DatasetSpec(
        BASE_URL, "transmission-generation-heat-map0", "coordinates", RecordsResponse[TransmissionHeatMapRecord]
    ),
}
