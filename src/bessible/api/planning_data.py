"""planning.data.gov.uk (MHCLG Planning Data platform) — entity + dataset search.

Docs: https://www.planning.data.gov.uk/docs  (OpenAPI: https://www.planning.data.gov.uk/openapi.json)
No API key. All geometries are WGS84 (EPSG:4326); JSON responses carry them as WKT strings.

The platform serialises missing values as "" (empty string) rather than null, and almost every
value (numbers, dates) as a string. Models here read "" as None (``NullMarkerResponse``) and let pydantic
coerce strings to real types.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated, Any, ClassVar, Literal, get_args

from pydantic import Discriminator, Field, RootModel, Tag, TypeAdapter

from .base import ApiRequest, ApiResponse, NullMarkerResponse

BASE_URL = "https://www.planning.data.gov.uk"

DateMatch = Literal["match", "before", "since", "empty"]

GeometryRelation = Literal[
    "within",
    "equals",
    "disjoint",
    "intersects",
    "touches",
    "contains",
    "covers",
    "coveredby",
    "overlaps",
    "crosses",
]

Period = Literal["all", "current", "historical"]

_GENERIC_TAG = "__generic__"


# ------------------------------------------ 1. Request ------------------------------------------ #


# GET /entity.json  (and /entity.geojson)


class EntitySearchRequest(ApiRequest):
    """Search entities: GET /entity.{json|geojson}.

    Docs: https://www.planning.data.gov.uk/docs#/Search%20entity

    List-typed params are repeatable on the wire (`dataset=a&dataset=b`); `params()` returns
    lists, which httpx encodes as repeated keys. Same params work for GEOJSON_URL.
    """

    URL: ClassVar[str] = f"{BASE_URL}/entity.json"
    GEOJSON_URL: ClassVar[str] = f"{BASE_URL}/entity.geojson"
    METHOD: ClassVar[str] = "GET"

    q: str | None = None  # postcode or UPRN
    typology: list[str] | None = None
    dataset: list[str] | None = None
    organisation_entity: list[int] | None = None
    entity: list[int] | None = None
    curie: list[str] | None = None  # "prefix:reference"
    prefix: list[str] | None = None
    reference: list[str] | None = None
    period: list[Period] | None = None
    quality: list[str] | None = None

    start_date_year: int | None = None
    start_date_month: int | None = None
    start_date_day: int | None = None
    start_date_match: DateMatch | None = None
    end_date_year: int | None = None
    end_date_month: int | None = None
    end_date_day: int | None = None
    end_date_match: DateMatch | None = None
    entry_date_year: int | None = None
    entry_date_month: int | None = None
    entry_date_day: int | None = None
    entry_date_match: DateMatch | None = None

    # Point-in-polygon: entities whose geometry intersects this WGS84 point (both required).
    longitude: float | None = None
    latitude: float | None = None
    geometry: list[str] | None = None  # WKT, EPSG:4326
    geometry_entity: list[int] | None = None
    geometry_reference: list[str] | None = None
    geometry_curie: list[str] | None = None
    geometry_relation: GeometryRelation | None = None  # server default "within"

    limit: int | None = Field(None, ge=1, le=500)  # server default 10
    offset: int | None = None
    field: list[str] | None = None  # wire (hyphenated) field names to include
    exclude_field: list[str] | None = None  # e.g. ["geometry"] to keep responses small


class EntityRequest(ApiRequest):
    """Fetch one entity by number: GET /entity/{entity}.json.

    Docs: https://www.planning.data.gov.uk/docs#/Get%20entity

    No query params. Unknown entity -> 404 (HTML body).
    """

    URL: ClassVar[str] = f"{BASE_URL}/entity/{{entity}}.json"
    METHOD: ClassVar[str] = "GET"

    entity: int  # path param

    def url(self) -> str:
        """Return the endpoint URL with the entity number filled in."""
        return self.URL.format(entity=self.entity)

    def params(self) -> dict[str, Any]:
        """Return no query params; the only input is the path param."""
        return {}


class DatasetListRequest(ApiRequest):
    """List datasets: GET /dataset.json.

    Docs: https://www.planning.data.gov.uk/docs#/List%20datasets
    """

    URL: ClassVar[str] = f"{BASE_URL}/dataset.json"
    METHOD: ClassVar[str] = "GET"

    dataset: list[str] | None = None
    field: list[str] | None = None
    exclude_field: list[str] | None = None
    include_typologies: bool | None = None  # server default true


class DatasetRequest(ApiRequest):
    """Fetch one dataset record: GET /dataset/{dataset}.json.

    Docs: https://www.planning.data.gov.uk/docs#/Get%20dataset
    """

    URL: ClassVar[str] = f"{BASE_URL}/dataset/{{dataset}}.json"
    METHOD: ClassVar[str] = "GET"

    dataset: str  # path param

    def url(self) -> str:
        """Return the endpoint URL with the dataset name filled in."""
        return self.URL.format(dataset=self.dataset)

    def params(self) -> dict[str, Any]:
        """Return no query params; the only input is the path param."""
        return {}


# ----------------------------------------- 2. Response ------------------------------------------ #


class EntitySearchResponse(ApiResponse):
    """Response of GET /entity.json."""

    entities: list[Entity]
    links: PageLinks = Field(default_factory=lambda: PageLinks())  # ruff: ignore[unnecessary-lambda] - PageLinks is defined below
    count: int | None = None  # total matches across all pages


class EntityGeoJsonResponse(ApiResponse):
    """Response of GET /entity.geojson — a FeatureCollection (plus non-standard `links`)."""

    type: Literal["FeatureCollection"]
    features: list[EntityFeature]
    links: PageLinks | None = None


# EntityResponse (GET /entity/{entity}.json) closes section 3: its shape is the union of the entity
# models there, which Python needs defined first.


class DatasetListResponse(ApiResponse):
    """Response of GET /dataset.json."""

    datasets: list[Dataset]
    # typology name -> datasets of that typology; omitted when include_typologies=false
    typologies: dict[str, TypologyDatasets] | None = None
    feedback_form_footer: bool | None = None  # website artefact


class DatasetResponse(RootModel["Dataset"]):
    """Response of GET /dataset/{dataset}.json: one flat dataset record, in `.root`."""


# ------------------------------------ 3. Response sub-models ------------------------------------ #


class EntityBase(NullMarkerResponse):
    """Fields common to every entity, whatever its dataset.

    Only `entity` is always present in practice, but `field=`/`exclude_field=` request params
    can strip anything, so everything is optional. Extras are forbidden, so a dataset with
    attributes of its own needs a model below before it can be parsed.
    """

    entity: int | None = None  # platform-wide unique entity number
    dataset: str | None = None
    typology: str | None = None  # geography | document | legal-instrument | category | ...
    name: str | None = None
    reference: str | None = None  # id within the dataset (e.g. ONS code, list entry number)
    prefix: str | None = None  # CURIE prefix; curie = f"{prefix}:{reference}"
    organisation_entity: int | None = Field(None, alias="organisation-entity")
    entry_date: date | None = Field(None, alias="entry-date")
    start_date: date | None = Field(None, alias="start-date")
    end_date: date | None = Field(None, alias="end-date")  # set => entity is historical
    quality: str | None = None  # e.g. "authoritative", "some"
    geometry: str | None = None  # WKT (usually MULTIPOLYGON), EPSG:4326, lon lat order
    point: str | None = None  # WKT "POINT (lon lat)", EPSG:4326
    description: str | None = None
    notes: str | None = None
    document_url: str | None = Field(None, alias="document-url")
    documentation_url: str | None = Field(None, alias="documentation-url")
    wikidata: str | None = None
    wikipedia: str | None = None


class TitleBoundary(EntityBase):
    """HM Land Registry INSPIRE index polygon. reference = INSPIRE id."""

    dataset: Literal["title-boundary"]


class GreenBelt(EntityBase):
    """Green belt designation polygon."""

    dataset: Literal["green-belt"]
    green_belt_core: str | None = Field(None, alias="green-belt-core")
    local_authority_district: str | None = Field(None, alias="local-authority-district")  # ONS code


class FloodRiskZone(EntityBase):
    """EA Flood Map for Planning zones."""

    dataset: Literal["flood-risk-zone"]
    flood_risk_level: str | None = Field(None, alias="flood-risk-level")  # "2" | "3"
    flood_risk_type: str | None = Field(None, alias="flood-risk-type")  # e.g. "Fluvial Models"


class AgriculturalLandClassification(EntityBase):
    """Natural England provisional agricultural land classification polygon."""

    dataset: Literal["agricultural-land-classification"]
    # "Grade 1".."Grade 5", "Non Agricultural", "Urban", "Exclusion"
    agricultural_land_classification_grade: str | None = Field(None, alias="agricultural-land-classification-grade")


class ConservationArea(EntityBase):
    """Conservation area polygon (Historic England / LPA supplied)."""

    dataset: Literal["conservation-area"]
    designation_date: date | None = Field(None, alias="designation-date")
    legislation: str | None = None  # documented, not seen live


class ListedBuilding(EntityBase):
    """Point dataset (Historic England). reference = NHLE list entry number."""

    dataset: Literal["listed-building"]
    listed_building_grade: Literal["I", "II*", "II"] | None = Field(None, alias="listed-building-grade")


class ListedBuildingOutline(EntityBase):
    """LPA-supplied polygons. Spec fields below were not seen in live samples."""

    dataset: Literal["listed-building-outline"]
    listed_building: str | None = Field(None, alias="listed-building")
    address_text: str | None = Field(None, alias="address-text")
    uprns: str | None = None


class ScheduledMonument(EntityBase):
    """Scheduled monument polygon (Historic England)."""

    dataset: Literal["scheduled-monument"]


class AreaOfOutstandingNaturalBeauty(EntityBase):
    """Area of Outstanding Natural Beauty (National Landscape) polygon."""

    dataset: Literal["area-of-outstanding-natural-beauty"]
    twitter: str | None = None
    website: str | None = None


class NationalPark(EntityBase):
    """National park boundary."""

    dataset: Literal["national-park"]


class SiteOfSpecialScientificInterest(EntityBase):
    """Site of Special Scientific Interest polygon (Natural England)."""

    dataset: Literal["site-of-special-scientific-interest"]


class SpecialAreaOfConservation(EntityBase):
    """Special Area of Conservation polygon."""

    dataset: Literal["special-area-of-conservation"]


class SpecialProtectionArea(EntityBase):
    """Special Protection Area polygon."""

    dataset: Literal["special-protection-area"]


class Ramsar(EntityBase):
    """Ramsar wetland site polygon."""

    dataset: Literal["ramsar"]
    ramsar: str | None = None  # UK site code, e.g. "UK11001"
    ramsar_site: str | None = Field(None, alias="ramsar-site")  # Ramsar convention site number
    special_protection_area: str | None = Field(None, alias="special-protection-area")


class AncientWoodland(EntityBase):
    """Ancient woodland inventory polygon (Natural England)."""

    dataset: Literal["ancient-woodland"]
    # ASNW = ancient semi-natural, PAWS = plantation on ancient woodland site, AWP = wood pasture
    ancient_woodland_status: str | None = Field(None, alias="ancient-woodland-status")


class LocalNatureReserve(EntityBase):
    """Local nature reserve polygon."""

    dataset: Literal["local-nature-reserve"]
    nature_reserve_status: str | None = Field(None, alias="nature-reserve-status")


class NationalNatureReserve(EntityBase):
    """National nature reserve polygon."""

    dataset: Literal["national-nature-reserve"]
    nature_reserve_status: str | None = Field(None, alias="nature-reserve-status")


class ParkAndGarden(EntityBase):
    """Registered historic park or garden (Historic England)."""

    dataset: Literal["park-and-garden"]
    park_and_garden_grade: Literal["I", "II*", "II"] | None = Field(None, alias="park-and-garden-grade")


class Battlefield(EntityBase):
    """Registered historic battlefield (Historic England)."""

    dataset: Literal["battlefield"]


class WorldHeritageSite(EntityBase):
    """UNESCO World Heritage Site boundary."""

    dataset: Literal["world-heritage-site"]
    world_heritage_convention_site: str | None = Field(None, alias="world-heritage-convention-site")  # UNESCO id


class WorldHeritageSiteBufferZone(EntityBase):
    """Buffer zone around a World Heritage Site."""

    dataset: Literal["world-heritage-site-buffer-zone"]
    world_heritage_site: str | None = Field(None, alias="world-heritage-site")  # reference of WHS


class HeritageCoast(EntityBase):
    """Heritage coast polygon."""

    dataset: Literal["heritage-coast"]


class TreePreservationZone(EntityBase):
    """Area covered by a tree preservation order."""

    dataset: Literal["tree-preservation-zone"]
    tree_preservation_order: str | None = Field(None, alias="tree-preservation-order")
    tree_preservation_zone_type: str | None = Field(None, alias="tree-preservation-zone-type")
    tree_species_list: str | None = Field(None, alias="tree-species-list")
    address_text: str | None = Field(None, alias="address-text")
    uprn: str | None = None


class Article4DirectionArea(EntityBase):
    """Area where an Article 4 direction removes permitted development rights."""

    dataset: Literal["article-4-direction-area"]
    article_4_direction: str | None = Field(None, alias="article-4-direction")
    permitted_development_rights: str | None = Field(None, alias="permitted-development-rights")
    address_texts: str | None = Field(None, alias="address-texts")
    uprns: str | None = None


class BrownfieldLand(EntityBase):
    """LPA brownfield land registers. Point-only (no polygon geometry)."""

    dataset: Literal["brownfield-land"]
    site_address: str | None = Field(None, alias="site-address")
    site_plan_url: str | None = Field(None, alias="site-plan-url")
    hectares: float | None = None
    deliverable: str | None = None  # "yes" or blank
    hazardous_substances: str | None = Field(None, alias="hazardous-substances")
    ownership_status: str | None = Field(None, alias="ownership-status")
    minimum_net_dwellings: int | None = Field(None, alias="minimum-net-dwellings")
    maximum_net_dwellings: int | None = Field(None, alias="maximum-net-dwellings")
    planning_permission_date: date | None = Field(None, alias="planning-permission-date")
    planning_permission_type: str | None = Field(None, alias="planning-permission-type")
    planning_permission_status: str | None = Field(None, alias="planning-permission-status")
    planning_permission_history: str | None = Field(None, alias="planning-permission-history")


class LocalPlanningAuthority(EntityBase):
    """reference = ONS LPA code (E60...)."""

    dataset: Literal["local-planning-authority"]
    region: str | None = None  # documented, not seen live


class LocalAuthorityDistrict(EntityBase):
    """reference = ONS LAD code (E06/E07/E08/E09...)."""

    dataset: Literal["local-authority-district"]


class Parish(EntityBase):
    """Civil parish boundary."""

    dataset: Literal["parish"]


class Ward(EntityBase):
    """Electoral ward boundary."""

    dataset: Literal["ward"]


class Region(EntityBase):
    """English region boundary."""

    dataset: Literal["region"]


class LocalPlan(EntityBase):
    """typology=legal-instrument: no geometry; link via local-plan-boundary / LPA codes."""

    dataset: Literal["local-plan"]
    adopted_date: date | None = Field(None, alias="adopted-date")
    period_start_date: date | None = Field(None, alias="period-start-date")
    period_end_date: date | None = Field(None, alias="period-end-date")
    local_plan_process: str | None = Field(None, alias="local-plan-process")
    local_plan_boundary: str | None = Field(None, alias="local-plan-boundary")
    local_planning_authorities: str | None = Field(None, alias="local-planning-authorities")  # ";"-separated LPA codes
    organisations: str | None = None  # ";"-separated organisation CURIEs
    required_housing: int | None = Field(None, alias="required-housing")


class _PlanBoundary(EntityBase):
    organisations: str | None = None  # ";"-separated organisation CURIEs


class LocalPlanBoundary(_PlanBoundary):
    """Area covered by a local plan."""

    dataset: Literal["local-plan-boundary"]
    local_planning_authorities: str | None = Field(None, alias="local-planning-authorities")  # ";"-separated LPA codes


class MineralsPlanBoundary(_PlanBoundary):
    """Area covered by a minerals plan."""

    dataset: Literal["minerals-plan-boundary"]


class WastePlanBoundary(_PlanBoundary):
    """Area covered by a waste plan."""

    dataset: Literal["waste-plan-boundary"]


class DevelopmentPlanDocument(EntityBase):
    """typology=document: no geometry."""

    dataset: Literal["development-plan-document"]
    development_plan: str | None = Field(None, alias="development-plan")
    document_types: str | None = Field(None, alias="document-types")  # ";"-separated


class PlanningApplication(EntityBase):
    """Patchy national coverage (only LPAs that publish to the platform)."""

    dataset: Literal["planning-application"]
    decision_date: date | None = Field(None, alias="decision-date")
    # Remaining fields are documented in the specification but were not seen live.
    address_text: str | None = Field(None, alias="address-text")
    uprn: str | None = None
    development_classification: str | None = Field(None, alias="development-classification")
    ground_area: str | None = Field(None, alias="ground-area")
    planning_application_status: str | None = Field(None, alias="planning-application-status")
    planning_application_type: str | None = Field(None, alias="planning-application-type")
    planning_decision: str | None = Field(None, alias="planning-decision")
    planning_decision_type: str | None = Field(None, alias="planning-decision-type")


class InfrastructureProject(EntityBase):
    """Nationally Significant Infrastructure Projects (Planning Inspectorate)."""

    dataset: Literal["infrastructure-project"]
    infrastructure_project_type: str | None = Field(None, alias="infrastructure-project-type")
    infrastructure_project_decision: str | None = Field(None, alias="infrastructure-project-decision")
    # documented, not seen live
    applicant_organisation: str | None = Field(None, alias="applicant-organisation")
    decision_date: date | None = Field(None, alias="decision-date")
    decision_maker: str | None = Field(None, alias="decision-maker")


class BuiltUpArea(EntityBase):
    """ONS built-up area polygon."""

    dataset: Literal["built-up-area"]


class HeritageAtRisk(EntityBase):
    """Historic England Heritage at Risk register entry."""

    dataset: Literal["heritage-at-risk"]


class ArchaeologicalPriorityArea(EntityBase):
    """Greater London only."""

    dataset: Literal["archaeological-priority-area"]
    archaeological_risk_tier: str | None = Field(None, alias="archaeological-risk-tier")


class CentralActivitiesZone(EntityBase):
    """London only."""

    dataset: Literal["central-activities-zone"]


class FloodStorageArea(EntityBase):
    """EA flood storage area polygon."""

    dataset: Literal["flood-storage-area"]


class MainRiver(EntityBase):
    """Dataset exists but had 0 entities when checked (2026-09); fields unverified."""

    dataset: Literal["main-river"]


def _entity_tag(v: object) -> str:
    ds = v.get("dataset") if isinstance(v, dict) else getattr(v, "dataset", None)
    return ds if ds in ENTITY_MODELS else _GENERIC_TAG


# Discriminated on `dataset`; field-stripped entities (and unmodelled datasets that only use the
# common fields) fall back to EntityBase.
type Entity = Annotated[
    Annotated[EntityBase, Tag(_GENERIC_TAG)]
    | Annotated[TitleBoundary, Tag("title-boundary")]
    | Annotated[GreenBelt, Tag("green-belt")]
    | Annotated[FloodRiskZone, Tag("flood-risk-zone")]
    | Annotated[AgriculturalLandClassification, Tag("agricultural-land-classification")]
    | Annotated[ConservationArea, Tag("conservation-area")]
    | Annotated[ListedBuilding, Tag("listed-building")]
    | Annotated[ListedBuildingOutline, Tag("listed-building-outline")]
    | Annotated[ScheduledMonument, Tag("scheduled-monument")]
    | Annotated[AreaOfOutstandingNaturalBeauty, Tag("area-of-outstanding-natural-beauty")]
    | Annotated[NationalPark, Tag("national-park")]
    | Annotated[SiteOfSpecialScientificInterest, Tag("site-of-special-scientific-interest")]
    | Annotated[SpecialAreaOfConservation, Tag("special-area-of-conservation")]
    | Annotated[SpecialProtectionArea, Tag("special-protection-area")]
    | Annotated[Ramsar, Tag("ramsar")]
    | Annotated[AncientWoodland, Tag("ancient-woodland")]
    | Annotated[LocalNatureReserve, Tag("local-nature-reserve")]
    | Annotated[NationalNatureReserve, Tag("national-nature-reserve")]
    | Annotated[ParkAndGarden, Tag("park-and-garden")]
    | Annotated[Battlefield, Tag("battlefield")]
    | Annotated[WorldHeritageSite, Tag("world-heritage-site")]
    | Annotated[WorldHeritageSiteBufferZone, Tag("world-heritage-site-buffer-zone")]
    | Annotated[HeritageCoast, Tag("heritage-coast")]
    | Annotated[TreePreservationZone, Tag("tree-preservation-zone")]
    | Annotated[Article4DirectionArea, Tag("article-4-direction-area")]
    | Annotated[BrownfieldLand, Tag("brownfield-land")]
    | Annotated[LocalPlanningAuthority, Tag("local-planning-authority")]
    | Annotated[LocalAuthorityDistrict, Tag("local-authority-district")]
    | Annotated[Parish, Tag("parish")]
    | Annotated[Ward, Tag("ward")]
    | Annotated[Region, Tag("region")]
    | Annotated[LocalPlan, Tag("local-plan")]
    | Annotated[LocalPlanBoundary, Tag("local-plan-boundary")]
    | Annotated[MineralsPlanBoundary, Tag("minerals-plan-boundary")]
    | Annotated[WastePlanBoundary, Tag("waste-plan-boundary")]
    | Annotated[DevelopmentPlanDocument, Tag("development-plan-document")]
    | Annotated[PlanningApplication, Tag("planning-application")]
    | Annotated[InfrastructureProject, Tag("infrastructure-project")]
    | Annotated[BuiltUpArea, Tag("built-up-area")]
    | Annotated[HeritageAtRisk, Tag("heritage-at-risk")]
    | Annotated[ArchaeologicalPriorityArea, Tag("archaeological-priority-area")]
    | Annotated[CentralActivitiesZone, Tag("central-activities-zone")]
    | Annotated[FloodStorageArea, Tag("flood-storage-area")]
    | Annotated[MainRiver, Tag("main-river")],
    Discriminator(_entity_tag),
]


class PageLinks(ApiResponse):
    """Pagination URLs. Empty object when everything fits in one page."""

    first: str | None = None
    last: str | None = None
    next: str | None = None
    prev: str | None = None


class GeoJsonGeometry(ApiResponse):
    """GeoJSON geometry object (RFC 7946)."""

    type: Literal[
        "Point",
        "MultiPoint",
        "LineString",
        "MultiLineString",
        "Polygon",
        "MultiPolygon",
        "GeometryCollection",
    ]
    coordinates: list[Any] | None = None  # [lon, lat] nesting per RFC 7946


class EntityFeature(ApiResponse):
    """GeoJSON Feature wrapping one entity."""

    type: Literal["Feature"]
    geometry: GeoJsonGeometry | None = None
    properties: Entity  # entity fields minus geometry/point


class EntityResponse(RootModel[Entity]):
    """Response of GET /entity/{entity}.json: one flat entity object (always with geometry).

    `.root` is the dataset-specific model.
    """


class PaintOptions(ApiResponse):
    """Map styling hints."""

    colour: str | None = None
    opacity: float | None = None
    weight: int | None = None
    type: str | None = None  # "point"


class Dataset(NullMarkerResponse):
    """One dataset record (shared by both dataset endpoints)."""

    dataset: str | None = None
    name: str | None = None
    plural: str | None = None
    typology: str | None = None
    collection: str | None = None
    description: str | None = None
    text: str | None = None  # markdown
    prefix: str | None = None
    themes: list[str] | None = None
    entity_count: int | None = Field(None, alias="entity-count")
    entity_minimum: int | None = Field(None, alias="entity-minimum")
    entity_maximum: int | None = Field(None, alias="entity-maximum")
    entities: str | None = None
    entry_date: date | None = Field(None, alias="entry-date")
    start_date: date | None = Field(None, alias="start-date")
    end_date: date | None = Field(None, alias="end-date")
    phase: str | None = None  # discovery | prioritised | alpha | beta | live
    realm: str | None = None  # dataset | specification | configuration | ...
    attribution: str | None = None
    attribution_text: str | None = Field(None, alias="attribution-text")
    licence: str | None = None
    licence_text: str | None = Field(None, alias="licence-text")
    consideration: str | None = None
    github_discussion: int | None = Field(None, alias="github-discussion")
    paint_options: PaintOptions | None = Field(None, alias="paint-options")
    replacement_dataset: str | None = Field(None, alias="replacement-dataset")
    version: str | None = None
    wikidata: str | None = None
    wikipedia: str | None = None


class TypologyDatasets(ApiResponse):
    """Datasets grouped under one typology in the dataset list response."""

    dataset: list[Dataset] = Field(default_factory=list)


# -------------------- 4. Not from the API (helpers, registries, transforms) --------------------- #


# dataset name -> model, read off the union above so it stays the single source of truth.
ENTITY_MODELS: dict[str, type[EntityBase]] = {
    get_args(member)[1].tag: get_args(member)[0]
    for member in get_args(get_args(Entity.__value__)[0])
    if get_args(member)[1].tag != _GENERIC_TAG
}


_entity_adapter: TypeAdapter[EntityBase] = TypeAdapter(Entity)


def parse_entity(data: object) -> EntityBase:
    """Validate one entity dict into its dataset-specific model (or EntityBase)."""
    return _entity_adapter.validate_python(data)


# Geography datasets worth an `/entity.json?latitude=..&longitude=..&dataset=..` point query
# for BESS siting. (main-river omitted: empty upstream. local-plan / development-plan-document
# omitted: no geometry — look them up via the LPA instead.)
BESS_POINT_DATASETS: tuple[str, ...] = (
    "title-boundary",
    "green-belt",
    "flood-risk-zone",
    "flood-storage-area",
    "agricultural-land-classification",
    "conservation-area",
    "listed-building",
    "listed-building-outline",
    "scheduled-monument",
    "heritage-at-risk",
    "park-and-garden",
    "battlefield",
    "world-heritage-site",
    "world-heritage-site-buffer-zone",
    "archaeological-priority-area",
    "area-of-outstanding-natural-beauty",
    "national-park",
    "heritage-coast",
    "site-of-special-scientific-interest",
    "special-area-of-conservation",
    "special-protection-area",
    "ramsar",
    "ancient-woodland",
    "local-nature-reserve",
    "national-nature-reserve",
    "tree-preservation-zone",
    "article-4-direction-area",
    "brownfield-land",
    "built-up-area",
    "central-activities-zone",
    "infrastructure-project",
    "planning-application",
    "local-planning-authority",
    "local-authority-district",
    "parish",
    "ward",
    "region",
)
