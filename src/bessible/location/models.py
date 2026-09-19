"""The tidy, BESS-specific view of a location: `Coordinates` in, `LocationData` out.

Built on top of the wire models in `bessible.api`: only what helps judge whether a site can take a battery is
kept, units and spellings are normalised across the data sources, and everything is measured against the title
boundary (the area under analysis) rather than the single input point.

`LocationData` is split in two on purpose:

    deterministic   measured or looked-up facts (polygons, distances, MW, grades). Safe to compute on in plain code.
    agentic         material for an agent to read and reason about (policy documents, PDFs, free-text notes,
                    search terms). Never feed these into arithmetic.

Distances are from the title boundary (0 when on the site), or from the input point when no title was found.
Geometry is GeoJSON, `[lon, lat]`, WGS84.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, Field

# --------------------------------------------- input -------------------------------------------- #


class Coordinates(BaseModel):
    """A WGS84 point. The only input. (Same shape as the pipeline's `Position`)."""

    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)


# ------------------------------------------- the site ------------------------------------------- #


class Geometry(BaseModel):
    """A GeoJSON geometry."""

    type: Literal["Point", "MultiPoint", "LineString", "MultiLineString", "Polygon", "MultiPolygon"]
    coordinates: list[Any]


class TitleBoundary(BaseModel):
    """The HM Land Registry INSPIRE polygon containing the point: the area every other figure is measured against."""

    inspire_id: str
    geometry: Geometry
    area_m2: float
    area_ha: float
    perimeter_m: float
    centroid: Coordinates
    bbox: tuple[float, float, float, float]  # min_lon, min_lat, max_lon, max_lat
    source_url: str


# ---------------------------------- deterministic: where it is ---------------------------------- #


class Locality(BaseModel):
    """Administrative geography. `country` and `planning_authority` decide the consenting regime."""

    address: str | None = None  # nearest OpenStreetMap address, human-readable
    place: str | None = None  # nearest settlement (hamlet / village / town / city)
    postcode: str | None = None  # nearest postcode
    postcode_distance_m: float | None = None
    country: str | None = None  # "England" | "Scotland" | "Wales"
    region: str | None = None
    county: str | None = None
    district: str | None = None
    parish: str | None = None
    ward: str | None = None
    constituency: str | None = None
    planning_authority: str | None = None
    planning_authority_code: str | None = None  # ONS code, e.g. "E60000299"
    rural_urban: str | None = None  # ONS 2021 rural-urban class of the postcode
    built_up_area: str | None = None  # set when the title touches a built-up area


# ------------------------------------ deterministic: the land ----------------------------------- #


class ElevationSample(BaseModel):
    """One labelled height inside the title (for the map)."""

    lat: float
    lon: float
    elevation_m: float


class Terrain(BaseModel):
    """Height and slope inside the title. Slope figures need the 1 m LIDAR, so they are None on the 90 m fallback."""

    source: Literal["ea_lidar_1m", "open_meteo_90m"]
    resolution_m: float
    cells: int  # raster cells (or sample points) inside the title
    min_m: float
    max_m: float
    mean_m: float
    relief_m: float  # max - min
    slope_median_pct: float | None = None
    slope_p90_pct: float | None = None
    slope_max_pct: float | None = None
    share_over_5pct: float | None = None  # 0-1 share of the title steeper than 5 %, a common platform limit
    samples: list[ElevationSample] = Field(default_factory=list)


class FloodZone(BaseModel):
    """One Environment Agency Flood Zone 2 / 3 polygon on or near the title."""

    zone: Literal[2, 3]
    flood_source: str | None = None  # "river" | "river and sea" ...
    origin: str | None = None  # "modelled" | "recorded" ...
    overlap_pct: float  # share of the title inside it, 0-100
    distance_m: float  # 0 when it touches the title


class FloodRisk(BaseModel):
    """Flood Map for Planning (England only; `None` on `Deterministic.flood` means not assessed, not Zone 1)."""

    zone: Literal[1, 2, 3]  # worst zone touching the title; 1 = none
    zone_2_pct: float  # share of the title in Flood Zone 2, 0-100
    zone_3_pct: float
    flood_storage_area: bool = False  # the title touches a designated flood storage area
    zones: list[FloodZone] = Field(default_factory=list)  # zones within the search margin, nearest first


class AlcGrade(BaseModel):
    """Agricultural land classification of part of the title."""

    grade: str  # "Grade 1".."Grade 5", "Grade 3a", "Grade 3b", "Non Agricultural", "Urban"
    overlap_pct: float  # share of the title, 0-100
    survey: Literal["provisional", "post_1988"]  # provisional = 1:250k and cannot split grade 3; post_1988 = surveyed


class Land(BaseModel):
    """Land quality and the designations that are a yes / no on the title."""

    alc: list[AlcGrade] = Field(default_factory=list)  # largest share first
    # Grades 1, 2 and 3a are "best and most versatile": policy steers development away. None = a provisional
    # "Grade 3" that no detailed survey has split into 3a / 3b.
    best_and_most_versatile: bool | None = None
    green_belt: bool = False
    green_belt_name: str | None = None
    brownfield: bool = False  # a brownfield register site lies on the title


DesignationCategory = Literal["ecology", "landscape", "heritage", "planning"]


class Designation(BaseModel):
    """One designated area or asset on or near the title (the map layers)."""

    kind: str  # e.g. "sssi", "ancient_woodland", "listed_building", "conservation_area", "article_4_direction"
    category: DesignationCategory
    name: str | None = None
    reference: str | None = None
    detail: str | None = None  # grade / status / habitat, e.g. "Grade II*", "ASNW"
    on_site: bool
    overlap_pct: float | None = None  # share of the title covered, 0-100; None when the geometry was not fetched
    distance_m: float | None = None  # 0 when on site; None when only known to touch the title
    source: Literal["natural_england", "planning_data"]
    source_url: str | None = None
    geometry: Geometry | None = None  # simplified, for the map


# ------------------------------------ deterministic: the grid ----------------------------------- #

Rag = Literal["red", "amber", "green"]
Operator = Literal["UKPN", "NGED", "SSEN Distribution", "SSEN Transmission"]


class Headroom(BaseModel):
    """Spare capacity at a substation as its network operator publishes it."""

    generation_mw: float | None = None  # export headroom
    generation_rag: Rag | None = None
    generation_constraint: str | None = None  # what limits it, e.g. "Thermal", "Upstream Thermal Capacity"
    demand: float | None = None  # import headroom, in `demand_unit`
    demand_unit: Literal["MW", "MVA"] = "MW"
    demand_rag: Rag | None = None
    demand_constraint: str | None = None
    basis: str  # how the operator defines the figures
    # Inputs to the capacity range (UKPN publishes all of them, the others only some).
    demand_firm_mw: float | None = None
    demand_max_mw: float | None = None
    demand_min_mw: float | None = None  # negative = the substation already exports at times
    generation_firm_mw: float | None = None
    reverse_power_available_mw: float | None = None
    # Connection pipeline at this substation (competition for the same headroom).
    generation_offers_accepted_mw: float | None = None
    generation_offers_made_mw: float | None = None
    generation_budget_estimates_mw: float | None = None
    demand_offers_accepted_mw: float | None = None
    demand_offers_made_mw: float | None = None
    demand_budget_estimates_mw: float | None = None
    connected_generation_mw: float | None = None
    contracted_generation_mw: float | None = None
    contracted_battery_demand_mva: float | None = None  # batteries already contracted to import here


class Substation(BaseModel):
    """A substation near the site, with its headroom where the operator publishes one."""

    name: str
    operator: Operator
    kind: str  # "primary" | "bsp" | "gsp" | "grid" | "transmission"
    voltage_kv: float | None = None  # highest voltage on site
    voltages: str | None = None  # as published, e.g. "33 / 11"
    coords: Coordinates
    distance_km: float
    bsp: str | None = None  # bulk supply point feeding it
    gsp: str | None = None  # grid supply point (the transmission interface)
    headroom: Headroom | None = None
    tia_threshold_mw: float | None = None  # above this, NESO must assess the transmission impact
    technical_limits_agreed: bool | None = None  # curtailable connections allowed ahead of transmission works
    transformer_ratings_summer_mva: list[float] = Field(default_factory=list)
    transformer_ratings_winter_mva: list[float] = Field(default_factory=list)
    max_demand_summer_mva: float | None = None
    max_demand_winter_mva: float | None = None
    earthing: Literal["HOT", "COLD"] | None = None  # HOT = high earth potential rise, costlier to connect near
    reinforcement: str | None = None  # planned works, as published
    reinforcement_due: str | None = None


class OverheadLine(BaseModel):
    """An overhead line near the site: a possible point of connection, and an easement if it crosses the title."""

    operator: Operator
    voltage_kv: float | None = None
    distance_m: float
    crosses_site: bool
    geometry: Geometry


class GridProject(BaseModel):
    """A generation / storage project on the embedded capacity register near the site (competes for headroom)."""

    name: str | None = None
    operator: Operator
    coords: Coordinates
    distance_km: float
    technology: str | None = None  # e.g. "Storage (Battery)", "Photovoltaic"
    is_storage: bool
    is_solar: bool
    capacity_mw: float | None = None
    storage_mwh: float | None = None
    status: Literal["connected", "accepted"] | None = None
    connected_on: date | None = None
    target_energisation: date | None = None
    max_export_mw: float | None = None
    max_import_mw: float | None = None
    flexible_connection: bool | None = None
    in_queue: bool | None = None
    primary: str | None = None
    bsp: str | None = None
    gsp: str | None = None


class TransmissionProject(BaseModel):
    """A project on the transmission entry capacity (TEC) register at one of the site's grid supply points."""

    name: str | None = None
    connection_site: str | None = None
    capacity_mw: float | None = None  # cumulative total capacity
    connected_mw: float | None = None
    status: str | None = None  # "Scoping" | "Awaiting Consents" | "Consents Approved" | "Built" ...
    plant_type: str | None = None
    is_storage: bool
    effective_from: date | None = None
    agreement_type: str | None = None  # "Direct Connection" | "Embedded"
    gate: int | None = None  # connections-reform gate (1 or 2)
    listed_on: Literal["NESO TEC", "SSEN TEC", "SSEN Embedded"]  # which register the row comes from


class Grid(BaseModel):
    """The electricity network around the site. Lists are nearest first."""

    operators: list[Operator] = Field(default_factory=list)  # operators with records near the site
    substations: list[Substation] = Field(default_factory=list)
    lines: list[OverheadLine] = Field(default_factory=list)
    projects: list[GridProject] = Field(default_factory=list)
    gsps: list[str] = Field(default_factory=list)  # grid supply point names the transmission queue was matched on
    transmission_queue: list[TransmissionProject] = Field(default_factory=list)  # largest first


class Deterministic(BaseModel):
    """Measured / looked-up facts. `None` = not assessed (no title, outside coverage, or the source failed)."""

    locality: Locality = Field(default_factory=Locality)
    terrain: Terrain | None = None
    flood: FloodRisk | None = None
    land: Land | None = None
    designations: list[Designation] = Field(default_factory=list)  # on site first, then nearest
    grid: Grid = Field(default_factory=Grid)


# -------------------------------------------- agentic ------------------------------------------- #

DocumentKind = Literal[
    "local_plan",  # the adopted / emerging local plan of the planning authority
    "article_4_direction",  # removes permitted development rights on the title
    "sssi_impact_risk_zone",  # Natural England's consultation rules for the zone the title is in
    "alc_survey_report",  # the detailed agricultural land survey covering the title
    "designation",  # citation / listing page of a designation on or near the title
    "brownfield_site_plan",
    "planning_application",
    "infrastructure_project",  # nationally significant infrastructure project nearby
]


class SourceDocument(BaseModel):
    """Something for an agent to open and read."""

    kind: DocumentKind
    title: str
    url: str
    relates_to: str | None = None  # the designation / authority it belongs to
    note: str | None = None  # free text the data source attached


class Agentic(BaseModel):
    """Inputs for agents: documents to read, free-text notes and search terms. Not for arithmetic."""

    documents: list[SourceDocument] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)  # free-text remarks from the data sources
    search_terms: list[str] = Field(default_factory=list)  # place names for local news / sentiment search


# ------------------------------------------ provenance ------------------------------------------ #


class SourceStatus(BaseModel):
    """One upstream request: what was asked and whether it worked. `url` doubles as an artifact source link."""

    name: str
    url: str
    status: Literal["ok", "failed", "skipped"]
    records: int | None = None
    detail: str | None = None  # error text, or why it was skipped


# -------------------------------------------- output -------------------------------------------- #


class LocationData(BaseModel):
    """Everything we know about a location that bears on building a battery there."""

    coords: Coordinates
    title: TitleBoundary | None = None  # None: no registered title at the point (or outside England and Wales)
    deterministic: Deterministic = Field(default_factory=Deterministic)
    agentic: Agentic = Field(default_factory=Agentic)
    sources: list[SourceStatus] = Field(default_factory=list)

    def without_geometry(self) -> dict[str, Any]:
        """JSON-ready dump with every polygon / line left out: small enough to put in a prompt."""
        stripped: dict[str, Any] = _strip(self.model_dump(mode="json", exclude_none=True))
        return stripped


def _strip(value: Any) -> Any:  # ruff: ignore[any-type] - walks arbitrary JSON
    if isinstance(value, dict):
        return {k: _strip(v) for k, v in value.items() if k not in {"geometry", "samples"}}
    if isinstance(value, list):
        return [_strip(v) for v in value]
    return value
