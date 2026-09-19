"""Coordinate -> title boundary -> map + every API response, written to one HTML page.

python scripts/site_report.py 51.246403 -2.198739 [grid_radius_km, default 10]

Base map is OpenTopoMap (OS-like, no key). Set OS_API_KEY to use real Ordnance Survey tiles instead.
UKPN_API_KEY (environment or the repo's .env) adds UK Power Networks substations, headroom, the embedded
capacity register and overhead lines; UKPN only covers London, the South East and the East of England.
NGED (South West, Wales, Midlands) and SSEN Distribution (central southern England, north Scotland) headroom and
capacity registers are always queried; NGED_API_KEY is sent if set.
SSEN_API_KEY adds SSEN Transmission substations, lines and its TEC / embedded registers (north of Scotland only).
Terrain is the Environment Agency 1 m LIDAR DTM (England); elsewhere it falls back to Open-Meteo's 90 m DEM.
"""

from __future__ import annotations

import html
import json
import math
import os
import sys
import webbrowser
from concurrent.futures import ThreadPoolExecutor
from operator import itemgetter
from pathlib import Path
from typing import TYPE_CHECKING, Any

import httpx

if TYPE_CHECKING:
    from pydantic import BaseModel

# Lets this run from any env with pydantic + httpx (e.g. conda), without installing the package.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from bessible.api import (
    ckan,
    ea_flood,
    ea_lidar,
    natural_england,
    neso,
    nged,
    nominatim,
    open_meteo,
    opendatasoft,
    planning_data,
    postcodes_io,
    ssen,
    ssen_distribution,
    ukpn,
)

RADIUS_M = 2000  # search radius for nearby features
UKPN_RADIUS_M = 10_000  # substations / headroom / capacity register
UKPN_LINES_M = 3000  # overhead lines
MAP_M = 1000  # side of the square the map opens on
SSEN_RADIUS_M = 25_000  # transmission substations are sparse
GRID_N = 10  # elevation labels on the map: GRID_N x GRID_N over the title's bounding box (Open-Meteo max 100 points)
LIDAR_MAX_PX = 250  # longer side of the LIDAR raster; plots under 250 m stay at the native 1 m
NESO_MAX_SITES = 4  # nearest distinct grid supply points matched against the TEC register
ARGS_LAT_LON = 2  # argv holds lat and lon; a third value is the grid search radius in km
MAX_STR = 200  # long strings in the tables are cut to this

# Natural England layers drawn on the map: name -> colour
NE_COLOURS = {
    "sssi": "#d81b60",
    "sac": "#8e24aa",
    "spa": "#5e35b1",
    "ramsar": "#1e88e5",
    "nnr": "#00897b",
    "lnr": "#43a047",
    "aonb": "#c0ca33",
    "national_parks": "#7cb342",
    "ancient_woodland_revised": "#2e7d32",
    "priority_habitats": "#9e9d24",
}


# ------------------------------------------------------------------------------------ fetching


def env(name: str) -> str | None:
    """A setting from the environment, else from the repo's .env file."""
    if os.environ.get(name):
        return os.environ[name]
    dotenv = Path(__file__).resolve().parents[1] / ".env"
    for line in dotenv.read_text(encoding="utf-8").splitlines() if dotenv.is_file() else []:
        key, _, value = line.partition("=")
        if key.strip() == name and value.strip():
            return value.strip().strip("'\"")
    return None


def fetch(client: httpx.Client, req: Any, resp: Any, url: str | None = None) -> BaseModel:
    """GET a request model and parse the body with its response model (or registry spec)."""
    address: str = url or (req.url() if callable(getattr(req, "url", None)) else req.URL)
    headers = None
    if isinstance(req, opendatasoft.RecordsRequest):  # Opendatasoft: the key depends on the portal
        key = env("SSEN_API_KEY" if req.base_url == ssen.BASE_URL else "UKPN_API_KEY")
        headers = opendatasoft.auth_headers(key or "")
    r = client.get(address, params=req.params(), headers=headers)
    r.raise_for_status()
    has_parse = isinstance(resp, (natural_england.LayerSpec, opendatasoft.DatasetSpec))
    return resp.parse(r.json()) if has_parse else resp.model_validate(r.json())


def fetch_nged(client: httpx.Client, req: Any, resp: Any, lat: float, lon: float, min_mw: float = 0) -> BaseModel:
    """NGED / SSEN Distribution have no spatial query: fetch the table, keep rows within UKPN_RADIUS_M (>= min_mw)."""
    is_ssen = isinstance(req, ssen_distribution.DatastoreSearchRequest)
    headers = ssen_distribution.HEADERS if is_ssen else nged.auth_headers(env("NGED_API_KEY") or "")
    r = client.get(req.URL, params=req.params(), headers=headers)
    r.raise_for_status()
    model = resp.model_validate(r.json())
    module = ssen_distribution if is_ssen else nged
    near = module.nearest(model.result.records, lat, lon, UKPN_RADIUS_M / 1000)
    model.result.records = [x for _, x in near if (getattr(x, "registered_capacity_1_mw", None) or min_mw) >= min_mw]
    return model


def fetch_ssen_lines(client: httpx.Client, lat: float, lon: float) -> BaseModel:
    """SSEN Distribution lines of 22 kV and above with any vertex within UKPN_LINES_M of the point."""
    req = ssen_distribution.lines_request()
    r = client.get(req.URL, params=req.params(), headers=ssen_distribution.HEADERS)
    r.raise_for_status()
    model = ssen_distribution.LinesResponse.model_validate(r.json())
    dlat, dlon = UKPN_LINES_M / 110_540, UKPN_LINES_M / (111_320 * math.cos(math.radians(lat)))
    result = model.result
    assert result is not None and isinstance(result.records, list)  # ruff: ignore[assert, pytest-composite-assertion] - narrows the CKAN union
    result.records = [
        ln
        for ln in result.records
        if ln.route_lat_long
        and any(
            abs(y - lat) <= dlat and abs(x - lon) <= dlon
            for x, y in ssen_distribution.linestring_coordinates(ln.route_lat_long)
        )
    ]
    return model


def calls(lat: float, lon: float) -> dict[str, tuple[Any, Any]]:
    """Section title -> (request, response model or LayerSpec)."""
    out: dict[str, tuple[Any, Any]] = {
        "Nominatim: address": (nominatim.ReverseRequest(lat=lat, lon=lon), nominatim.ReverseResponse),
        "Postcodes.io: nearest postcode": (
            postcodes_io.ReverseGeocodeRequest(lat=lat, lon=lon, widesearch=True, limit=1),
            postcodes_io.ReverseGeocodeResponse,
        ),
        "Planning Data: entities at point": (
            planning_data.EntitySearchRequest(
                latitude=lat, longitude=lon, geometry_relation="intersects", exclude_field=["geometry"], limit=100
            ),
            planning_data.EntitySearchResponse,
        ),
        "EA: flood zone at point (none = Zone 1)": (
            ea_flood.flood_zone_at_point(lat, lon),
            ea_flood.FloodZoneResponse,
        ),
    }
    for name, spec in natural_england.LAYERS.items():
        req = spec.at_point(lat, lon, RADIUS_M)
        req.return_geometry = name in NE_COLOURS
        req.max_allowable_offset = 0.00001  # ~1 m: trims huge designations without visibly distorting small ones
        req.geometry_precision = 6
        out[f"Natural England: {name} ({RADIUS_M} m)"] = (req, spec)
    if env("UKPN_API_KEY"):
        for name, spec in ukpn.DATASETS.items():
            radius = UKPN_LINES_M if "lines" in name else UKPN_RADIUS_M
            out[f"UKPN: {name} ({radius / 1000:g} km)"] = (spec.near(lat, lon, radius), spec)
    if env("SSEN_API_KEY"):
        for name, spec in ssen.DATASETS.items():
            out[f"SSEN: {name} ({SSEN_RADIUS_M / 1000:g} km)"] = (spec.near(lat, lon, SSEN_RADIUS_M), spec)
    return out


# ------------------------------------------------------------------------------------ geometry


def rings(geom: dict[str, Any]) -> list[list[list[list[float]]]]:
    """Polygons of a GeoJSON Polygon/MultiPolygon, each a list of rings of [lon, lat]."""
    return [geom["coordinates"]] if geom["type"] == "Polygon" else geom["coordinates"]


def in_ring(lon: float, lat: float, ring: list[list[float]]) -> bool:
    """Ray-casting point-in-ring test."""
    inside = False
    for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1], strict=True):
        if (y1 > lat) != (y2 > lat) and lon < (x2 - x1) * (lat - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


def in_geom(lon: float, lat: float, geom: dict[str, Any]) -> bool:
    """Whether a point is inside a GeoJSON Polygon / MultiPolygon (holes excluded)."""
    return any(
        in_ring(lon, lat, poly[0]) and not any(in_ring(lon, lat, hole) for hole in poly[1:]) for poly in rings(geom)
    )


def area_ha(geom: dict[str, Any]) -> float:
    """Approximate area in hectares (shoelace on a local equirectangular projection)."""
    total = 0.0
    for poly in rings(geom):
        for i, ring in enumerate(poly):
            k = 111_320 * math.cos(math.radians(ring[0][1]))
            pts = [(x * k, y * 110_540) for x, y in ring]
            a = abs(sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1], strict=True))) / 2
            total += a if i == 0 else -a
    return total / 10_000


def km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km."""
    a = (
        math.sin(math.radians(lat2 - lat1) / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    )
    return 6371 * 2 * math.asin(math.sqrt(a))


def bbox(geom: dict[str, Any]) -> tuple[float, float, float, float]:
    """(min_lon, min_lat, max_lon, max_lat) of a polygon's outer rings."""
    pts = [p for poly in rings(geom) for p in poly[0]]
    lons, lats = [p[0] for p in pts], [p[1] for p in pts]
    return min(lons), min(lats), max(lons), max(lats)


def lidar_terrain(client: httpx.Client, geom: dict[str, Any]) -> tuple[list[dict[str, float]], dict[str, Any]]:
    """EA 1 m LIDAR inside the title: map labels on a GRID_N grid, and height / slope stats over every cell."""
    w, s, e, n = bbox(geom)
    req = ea_lidar.dtm_for_bbox(s, w, n, e, LIDAR_MAX_PX)
    r = client.get(req.URL, params=req.params())
    r.raise_for_status()  # HTTP 500 = outside the LIDAR coverage (not England)
    dtm = ea_lidar.DtmGrid.from_geotiff(r.content)
    heights: list[float] = []
    slopes: list[float] = []
    for row in range(dtm.height):
        for col in range(dtm.width):
            lat, lon = dtm.centre(row, col)
            if (m := dtm.rows[row][col]) is not None and in_geom(lon, lat, geom):
                heights.append(m)
                if (sl := dtm.slope_percent(row, col)) is not None:
                    slopes.append(sl)
    if not heights:
        msg = "LIDAR raster has no data inside the title"
        raise ValueError(msg)
    slopes.sort()
    stats = {
        "source": "EA LIDAR Composite DTM",
        "cell_m": round(max(dtm.pixel_m), 2),
        "cells_in_title": len(heights),
        "min_m": min(heights),
        "max_m": max(heights),
        "median_slope_percent": round(slopes[len(slopes) // 2], 1) if slopes else None,
        "p90_slope_percent": round(slopes[int(len(slopes) * 0.9)], 1) if slopes else None,
        "share_over_5_percent": round(sum(x > 5 for x in slopes) / len(slopes), 2) if slopes else None,  # ruff: ignore[magic-value-comparison]
    }
    labels = [
        {"lat": y, "lon": x, "m": m}
        for i in range(GRID_N)
        for j in range(GRID_N)
        if in_geom(x := w + (e - w) * (i + 0.5) / GRID_N, y := s + (n - s) * (j + 0.5) / GRID_N, geom)
        and (m := dtm.at(y, x)) is not None
    ]
    return labels, stats


def elevation_grid(client: httpx.Client, geom: dict[str, Any]) -> list[dict[str, float]]:
    """Open-Meteo fallback: elevations on a regular grid over the title's bounding box, inside points only."""
    pts = [p for poly in rings(geom) for p in poly[0]]
    lons, lats = [p[0] for p in pts], [p[1] for p in pts]
    grid = [
        (
            min(lons) + (max(lons) - min(lons)) * (i + 0.5) / GRID_N,
            min(lats) + (max(lats) - min(lats)) * (j + 0.5) / GRID_N,
        )
        for i in range(GRID_N)
        for j in range(GRID_N)
    ]
    inside = [(x, y) for x, y in grid if in_geom(x, y, geom)]
    if not inside:
        return []
    req = open_meteo.ElevationRequest(latitude=[y for _, y in inside], longitude=[x for x, _ in inside])
    resp = fetch(client, req, open_meteo.ElevationResponse)
    return [{"lat": y, "lon": x, "m": m} for (x, y), m in zip(inside, resp.elevation, strict=True)]  # type: ignore[attr-defined]


# ------------------------------------------------------------------------------------ rendering


def render(v: Any) -> str:
    """Nested dicts / lists as HTML tables; geometry is left out and long strings are cut."""
    if isinstance(v, dict):
        rows = "".join(
            f"<tr><th>{html.escape(str(k))}</th><td>{render(x)}</td></tr>" for k, x in v.items() if k != "geometry"
        )
        return f"<table class=kv>{rows}</table>" if rows else "<i>empty</i>"
    if isinstance(v, list):
        if not v:
            return "<i>none</i>"
        if all(isinstance(x, dict) for x in v):
            cols = list(dict.fromkeys(k for x in v for k in x if k != "geometry"))
            head = "".join(f"<th>{html.escape(c)}</th>" for c in cols)
            body = "".join("<tr>" + "".join(f"<td>{render(x.get(c, ''))}</td>" for c in cols) + "</tr>" for x in v)
            return f"<table><tr>{head}</tr>{body}</table>"
        return ", ".join(render(x) for x in v)
    s = str(v)
    if s.startswith("http"):
        return f'<a href="{html.escape(s)}">{html.escape(s[:60])}</a>'
    return html.escape(s if len(s) <= MAX_STR else s[:MAX_STR] + "…")


CSS = """
body{font:14px system-ui;margin:2rem;color:#222} h1{font-size:1.4rem} #map{height:820px;border:1px solid #ccc;
border-radius:6px;margin:.6rem 0} .facts{margin:.4rem 0;color:#444}
details{margin:.6rem 0;border:1px solid #ddd;border-radius:6px;padding:.4rem .8rem}
summary{font-weight:600;cursor:pointer} summary small{font-weight:400;color:#777}
.err summary{color:#b00} pre{white-space:pre-wrap}
table{border-collapse:collapse;margin:.4rem 0;font-size:13px} td,th{border:1px solid #e3e3e3;padding:3px 7px;
text-align:left;vertical-align:top} th{background:#f6f6f6} .kv>tbody>tr>th{width:1%;white-space:nowrap}
.ico{font-size:18px;line-height:18px;text-shadow:0 0 3px #fff,0 0 3px #fff}
.elev span{display:block;font:9px/14px system-ui;text-align:center;border-radius:7px;border:1px solid #0006;color:#000}
"""

MAP_JS = """
const D = JSON.parse(document.getElementById('data').textContent);
const topo = L.tileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png',
  {maxZoom: 17, attribution: '© OpenTopoMap (CC-BY-SA), © OpenStreetMap'});
const aerial = L.tileLayer(
  'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
  {maxZoom: 19, attribution: 'Imagery © Esri, Maxar, Earthstar Geographics'});
const bases = {'Topographic': topo, 'Aerial': aerial};
if (D.osKey) {
  bases['Ordnance Survey'] = L.tileLayer(
    `https://api.os.uk/maps/raster/v1/zxy/Outdoor_3857/{z}/{x}/{y}.png?key=${D.osKey}`,
    {maxZoom: 20, attribution: '© Crown copyright and database rights Ordnance Survey'});
}
const base = bases['Ordnance Survey'] || topo;
const map = L.map('map', {layers: [base]}).fitBounds(D.square);  // view first: layers need it to draw
const overlays = {};
const props = p => Object.entries(p).filter(([k, v]) => v !== null && v !== '' && typeof v !== 'object')
  .slice(0, 12).map(([k, v]) => `<b>${k}</b>: ${v}`).join('<br>');

for (const [name, l] of Object.entries(D.ne)) {
  overlays[`<span style="color:${l.colour}">■</span> ${name}`] = L.geoJSON(l.features, {
    style: {color: l.colour, weight: 1.5, fillOpacity: 0.25},
    onEachFeature: (f, lyr) => lyr.bindPopup(`<b>${name}</b><br>${props(f.properties)}`),
  }).addTo(map);
}
// UK Power Networks
const RAG = {RED: '#d32f2f', AMBER: '#f9a825', GREEN: '#2e7d32'};
const icon = html => L.divIcon({className: 'ico', html, iconSize: [18, 18]});
if (D.ukpn) {
  const U = D.ukpn;
  overlays['<span style="color:#6a1b9a">━</span> 132 kV / <span style="color:#ef6c00">━</span> 33 kV / <span style="color:#c62828">━</span> other overhead lines'] =
    L.geoJSON(U.lines, {style: f => ({color: {'33kV': '#ef6c00', '132kV': '#6a1b9a'}[f.properties.voltage] || '#c62828', weight: 3}),
      onEachFeature: (f, lyr) => lyr.bindPopup(`<b>${f.properties.voltage} overhead line</b>`)}).addTo(map);
  overlays['🔌 substations'] = L.layerGroup(U.substations.map(s => L.marker([s.lat, s.lon], {icon: icon('🔌')})
    .bindPopup(`<b>${s.name}</b><br>${s.type}, ${s.kv} kV<br>${s.km} km from the point`))).addTo(map);
  overlays['● substation headroom (generation)'] = L.layerGroup(U.headroom.map(h => L.circleMarker([h.lat, h.lon],
    {radius: 11, weight: 2, color: '#222', fillColor: RAG[h.gen_rag] || '#999', fillOpacity: 0.85})
    .bindPopup(`<b>${h.name}</b> (${h.km} km)<br>generation headroom: <b>${h.gen_mw} MW</b> (${h.gen_rag}, ${h.gen_limit})` +
      `<br>demand headroom: <b>${h.dem_mw} MW</b> (${h.dem_rag}, ${h.dem_limit})<br>BSP ${h.bsp} · GSP ${h.gsp}`))).addTo(map);
  overlays['🔋 embedded capacity register (≥1 MW)'] = L.layerGroup(U.ecr.map(e => L.marker([e.lat, e.lon],
    {icon: icon(e.storage ? '🔋' : e.solar ? '☀️' : '⚡')})
    .bindPopup(`<b>${e.site}</b> (${e.km} km)<br>${e.tech}<br>${e.mw} MW · ${e.status}<br>via ${e.primary}`))).addTo(map);
  if (U.substations.length) {
    const n = U.substations[0];
    L.polyline([D.point, [n.lat, n.lon]], {color: '#222', weight: 1.5, dashArray: '6'})
      .bindTooltip(`${n.km} km to ${n.name}`, {sticky: true}).addTo(map);
  }
}

if (D.title) {
  overlays['Title boundary'] = L.geoJSON(D.title, {style: {color: '#e60000', weight: 3, fillOpacity: 0.08}})
    .bindPopup(D.titlePopup).addTo(map);
}
if (D.elev.length) {
  const ms = D.elev.map(e => e.m), lo = Math.min(...ms), hi = Math.max(...ms);
  overlays[`Elevation grid (${lo}–${hi} m)`] = L.layerGroup(D.elev.map(e => {
    const t = hi > lo ? (e.m - lo) / (hi - lo) : 0.5;
    return L.marker([e.lat, e.lon], {icon: L.divIcon({className: 'elev', iconSize: [22, 14],
      html: `<span style="background:hsl(${(1 - t) * 220}, 85%, 60%)">${Math.round(e.m)}</span>`})});
  })).addTo(map);
}
L.rectangle(D.square, {color: '#000', weight: 1, dashArray: '4', fill: false}).addTo(map);
L.marker(D.point).bindPopup(`${D.point[0]}, ${D.point[1]}`).addTo(map);
L.control.layers(bases, overlays, {collapsed: false}).addTo(map);
if (D.ukpn && D.ukpn.substations.length) {
  const b = L.control({position: 'bottomleft'});
  b.onAdd = () => {
    const el = L.DomUtil.create('button');
    el.textContent = 'Zoom to nearest substation';
    el.onclick = () => map.fitBounds([D.point, [D.ukpn.substations[0].lat, D.ukpn.substations[0].lon]], {padding: [60, 60]});
    return el;
  };
  b.addTo(map);
}
L.control.scale({imperial: false}).addTo(map);
"""


def main() -> None:
    """Fetch everything for one coordinate and write the report page."""
    lat, lon = (
        (float(x.strip(",")) for x in sys.argv[1:3])
        if len(sys.argv) > ARGS_LAT_LON
        else map(float, input("lat, lon: ").replace(",", " ").split())
    )
    if len(sys.argv) > ARGS_LAT_LON + 1:  # optional grid search radius in km (substations, headroom, registers)
        global UKPN_RADIUS_M  # ruff: ignore[global-statement]
        UKPN_RADIUS_M = int(float(sys.argv[3]) * 1000)
    sections: list[str] = []
    results: dict[str, BaseModel] = {}

    def add(title: str, model: BaseModel) -> None:
        body = render(model.model_dump(mode="json", exclude_none=True))
        sections.append(
            f"<details><summary>{html.escape(title)} <small>{type(model).__name__}</small></summary>{body}</details>"
        )
        results[title] = model
        print("ok  ", title)

    def fail(title: str, e: Exception) -> None:
        sections.append(
            f"<details open class=err><summary>{html.escape(title)} — FAILED</summary>"
            f"<pre>{html.escape(f'{type(e).__name__}: {e}')}</pre></details>"
        )
        print("FAIL", title)

    title_geom: dict[str, Any] | None = None
    title_popup = ""
    elev: list[dict[str, float]] = []
    terrain: dict[str, Any] = {}
    with (
        httpx.Client(timeout=60, headers={"User-Agent": "bessible-site-report"}) as client,
        ThreadPoolExecutor(8) as ex,
    ):
        futures = {title: ex.submit(fetch, client, *pair) for title, pair in calls(lat, lon).items()}
        km10 = f"{UKPN_RADIUS_M / 1000:g} km"
        futures[f"NGED: capacity_map ({km10})"] = ex.submit(
            fetch_nged, client, nged.capacity_map_request(), nged.CapacityMapResponse, lat, lon
        )
        futures[f"NGED: embedded_capacity_register (>=1 MW, {km10})"] = ex.submit(
            fetch_nged, client, nged.ecr_request(), nged.EcrResponse, lat, lon, 1
        )
        sd = ssen_distribution
        futures[f"SSEN Distribution: headroom ({km10})"] = ex.submit(
            fetch_nged, client, sd.headroom_request(), sd.HeadroomResponse, lat, lon
        )
        futures[f"SSEN Distribution: overhead_lines_22kv_plus ({UKPN_LINES_M / 1000:g} km)"] = ex.submit(
            fetch_ssen_lines, client, lat, lon
        )
        futures[f"SSEN Distribution: embedded_capacity_register ({km10})"] = ex.submit(
            fetch_nged, client, sd.ecr_request(), sd.EcrResponse, lat, lon
        )

        # The site itself: the title boundary polygon containing the point, then elevations inside it.
        name = "Planning Data: title boundary containing the point"
        try:
            req = planning_data.EntitySearchRequest(
                latitude=lat, longitude=lon, dataset=["title-boundary"], geometry_relation="intersects"
            )
            tb = fetch(client, req, planning_data.EntityGeoJsonResponse, url=req.GEOJSON_URL)
            add(name, tb)
            feats = [f for f in tb.features if f.geometry]  # type: ignore[attr-defined]
            if feats:
                geom: dict[str, Any] = feats[0].geometry.model_dump(mode="json")
                title_geom = geom
                ref = feats[0].properties.reference
                title_popup = f"<b>Title boundary</b><br>INSPIRE id {ref}<br>~{area_ha(geom):.2f} ha"
        except Exception as e:  # ruff: ignore[blind-except] - show every failure on the page
            fail(name, e)
        if title_geom:
            name = "EA LIDAR: 1 m terrain inside the title"
            try:
                elev, terrain = lidar_terrain(client, title_geom)
            except Exception as e:  # ruff: ignore[blind-except] - not England, or the service is down: use the coarse DEM
                print("skip", name, f"({type(e).__name__}: {e})"[:120])
                name = "Open-Meteo: elevation grid inside the title (90 m DEM, LIDAR unavailable)"
                try:
                    elev = elevation_grid(client, title_geom)
                    terrain = {"source": "Open-Meteo 90 m DEM", "points": len(elev)}
                except Exception as e2:  # ruff: ignore[blind-except]
                    fail(name, e2)
            if elev:
                sections.append(
                    f"<details><summary>{html.escape(name)} <small>{len(elev)} map labels</small></summary>"
                    f"{render(terrain)}{render(elev)}</details>"
                )
                print("ok  ", name)

        for title, fut in futures.items():
            try:
                add(title, fut.result())
            except Exception as e:  # ruff: ignore[blind-except]
                fail(title, e)

        # Second round: the transmission registers have no coordinates, so they are matched on the
        # names of the grid supply points / substations found above.
        heat = next((m.results for t, m in results.items() if t.startswith("UKPN: capacity_heatmap")), [])  # type: ignore[attr-defined]
        ssen_subs = sorted(
            (s for t, m in results.items() if t.startswith("SSEN: substations") for s in m.results if s.geo_point_2d),  # type: ignore[attr-defined]
            key=lambda s: km(lat, lon, s.geo_point_2d.lat, s.geo_point_2d.lon),
        )
        sites = list(dict.fromkeys(h.gsp for h in heat if h.gsp and h.gsp != "-"))
        nged_cap = next((m.result.records for t, m in results.items() if t.startswith("NGED: capacity_map")), [])  # type: ignore[attr-defined]
        sites += [nged.clean_site_name(h.gsp) for h in nged_cap if h.gsp]
        sd_head = next((m.result.records for t, m in results.items() if t.startswith("SSEN Distribution: head")), [])  # type: ignore[attr-defined]
        sites += [sd.clean_site_name(h.upstream_gsp) for h in sd_head if h.upstream_gsp]
        sites += [s.name.removesuffix(" SUBSTATION").title() for s in ssen_subs if s.name]
        sites = list(dict.fromkeys(sites))[:NESO_MAX_SITES]
        if sites:
            name = f"NESO: TEC register at {', '.join(sites)}"
            try:
                add(
                    name,
                    fetch(client, neso.tec_at_sites(sites), ckan.DatastoreSearchSqlResponse[neso.TecRegisterRecord]),
                )
            except Exception as e:  # ruff: ignore[blind-except]
                fail(name, e)
        else:
            print("skip NESO: no grid supply point name known for this point (needs DNO data)")
        if ssen_subs:
            for reg in ssen.REGISTERS:
                name = f"SSEN: {reg} at {ssen_subs[0].name}"
                try:
                    r = client.get(
                        (req := ssen.register_request(reg, ssen_subs[0].name)).url(),
                        params=req.params(),
                        headers=opendatasoft.auth_headers(env("SSEN_API_KEY") or ""),
                    )
                    r.raise_for_status()
                    add(name, ssen.parse_register(r.json()))
                except Exception as e:  # ruff: ignore[blind-except]
                    fail(name, e)

    # Map data
    ne: dict[str, Any] = {}
    for title, model in results.items():
        layer = title.removeprefix("Natural England: ").split(" ")[0]
        if title.startswith("Natural England") and layer in NE_COLOURS:
            feats = [f for f in model.model_dump(mode="json", exclude_none=True)["features"] if f.get("geometry")]
            if feats:
                ne[layer] = {"colour": NE_COLOURS[layer], "features": feats}
    grid: dict[str, Any] | None = None
    if any(t.startswith(("UKPN", "SSEN", "NGED")) for t in results):  # "SSEN" covers both SSEN portals

        def rows(name: str) -> list[Any]:
            return next((m.results for t, m in results.items() if t.startswith(f"UKPN: {name} ")), [])  # type: ignore[attr-defined]

        def dist(p: Any) -> float:
            return round(km(lat, lon, p.lat, p.lon), 2)

        grid = {
            "substations": [
                {"lat": p.lat, "lon": p.lon, "name": s.sitename, "type": s.sitetype, "kv": s.sitevoltage, "km": dist(p)}
                for s in rows("substations")
                if (p := s.spatial_coordinates)
            ]
            + sorted(
                (
                    {
                        "lat": p.lat,
                        "lon": p.lon,
                        "name": s.name,
                        "type": "SSEN Transmission",
                        "kv": (s.voltage or 0) // 1000,
                        "km": dist(p),
                    }
                    for t, m in results.items()
                    if t.startswith("SSEN: substations")
                    for s in m.results  # type: ignore[attr-defined]
                    if (p := s.geo_point_2d)
                ),
                key=itemgetter("km"),
            ),
            "headroom": [
                {
                    "lat": p.lat,
                    "lon": p.lon,
                    "name": h.name,
                    "km": dist(p),
                    "bsp": h.bsp,
                    "gsp": h.gsp,
                    "gen_mw": h.generationavailablecapacity,
                    "gen_rag": h.generationconstraint,
                    "gen_limit": h.generationconstraintlimitingfactor,
                    "dem_mw": h.demandavailablecapacity,
                    "dem_rag": h.demandconstraint,
                    "dem_limit": h.demandconstraintlimitingfactor,
                }
                for h in rows("capacity_heatmap")
                if (p := h.geo_point_2d)
            ],
            "ecr": [
                {
                    "lat": p.lat,
                    "lon": p.lon,
                    "site": e.customer_site,
                    "km": dist(p),
                    "primary": e.primary,
                    "tech": e.energy_conversion_technology_1,
                    "mw": e.registered_capacity_1_mw,
                    "status": e.connection_status,
                    "storage": (e.energy_source_1 or "").startswith("Stored"),
                    "solar": e.energy_source_1 == "Solar",
                }
                for e in rows("embedded_capacity_register")
                if (p := e.spatialcoordinates_customer)
            ],
            "lines": [
                {
                    "type": "Feature",
                    "geometry": ln.geo_shape.geometry.model_dump(),
                    "properties": {"voltage": ln.voltage},
                }
                for name in ("overhead_lines_132kv", "overhead_lines_33kv")
                for ln in rows(name)
                if ln.geo_shape
            ]
            + [
                {
                    "type": "Feature",
                    "geometry": ln.geo_shape.geometry.model_dump(),
                    "properties": {"voltage": f"{(ln.voltage or 0) // 1000}kV"},
                }
                for t, m in results.items()
                if t.startswith("SSEN: overhead_lines")
                for ln in m.results  # type: ignore[attr-defined]
                if ln.geo_shape
            ]
            + [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": ssen_distribution.linestring_coordinates(ln.route_lat_long),
                    },
                    "properties": {"voltage": (ln.nominal_voltage_pp or "").replace(".000 ", "")},
                }
                for t, m in results.items()
                if t.startswith("SSEN Distribution: overhead_lines")
                for ln in m.result.records  # type: ignore[attr-defined]
            ],
        }
        nged_ecr = next((m.result.records for t, m in results.items() if t.startswith("NGED: embedded")), [])  # type: ignore[attr-defined]
        for h in nged_cap:
            d = round(km(lat, lon, h.latitude, h.longitude), 2)
            grid["substations"].append({
                "lat": h.latitude,
                "lon": h.longitude,
                "name": h.name,
                "type": f"NGED {h.type}",
                "kv": "?",
                "km": d,
            })
            grid["headroom"].append({
                "lat": h.latitude,
                "lon": h.longitude,
                "name": h.name,
                "km": d,
                "bsp": h.bsp,
                "gsp": h.gsp,
                "gen_mw": h.generation_contracted_headroom_mw,
                "gen_rag": (h.generation_contracted_rag or "").upper(),
                "gen_limit": "after contracted schemes",
                "dem_mw": h.demand_contracted_headroom_mw,
                "dem_rag": (h.demand_contracted_rag or "").upper(),
                "dem_limit": "after contracted schemes",
            })
        grid["ecr"] += [
            {
                "lat": e.lat,
                "lon": e.lon,
                "site": e.customer_site,
                "km": round(km(lat, lon, e.lat, e.lon), 2),
                "primary": e.primary,
                "tech": e.energy_conversion_technology_1,
                "mw": e.registered_capacity_1_mw,
                "status": e.connection_status,
                "storage": (e.energy_source_1 or "").startswith("Stored"),
                "solar": e.energy_source_1 == "Solar",
            }
            for e in nged_ecr
        ]
        for h in sd_head:
            d = round(km(lat, lon, h.lat, h.lon), 2)
            grid["substations"].append({
                "lat": h.lat,
                "lon": h.lon,
                "name": h.substation,
                "type": f"SSEN {h.substation_type}",
                "kv": h.voltage_kv,
                "km": d,
            })
            grid["headroom"].append({
                "lat": h.lat,
                "lon": h.lon,
                "name": h.substation,
                "km": d,
                "bsp": h.upstream_bsp,
                "gsp": h.upstream_gsp,
                "gen_mw": h.estimated_generation_headroom_mw,
                "gen_rag": (h.substation_generation_rag_status or "").upper(),
                "gen_limit": h.generation_constraint,
                "dem_mw": h.estimated_demand_headroom_mva,
                "dem_rag": (h.substation_demand_rag_status or "").upper(),
                "dem_limit": h.demand_constraint,
            })
        sd_ecr = next((m.result.records for t, m in results.items() if t.startswith("SSEN Distribution: emb")), [])  # type: ignore[attr-defined]
        grid["ecr"] += [
            {
                "lat": e.lat,
                "lon": e.lon,
                "site": (e.customer_site or "").strip().title(),
                "km": round(km(lat, lon, e.lat, e.lon), 2),
                "primary": e.primary,
                "tech": (e.energy_conversion_technology_1 or "").title(),
                "mw": e.registered_capacity_1_mw,
                "status": (e.connection_status or "").capitalize(),
                "storage": (e.energy_source_1 or "").startswith("STORED"),
                "solar": e.energy_source_1 == "SOLAR",
            }
            for e in sd_ecr
        ]
        for key in ("substations", "headroom", "ecr"):
            grid[key].sort(key=itemgetter("km"))
    dlat, dlon = MAP_M / 2 / 110_540, MAP_M / 2 / (111_320 * math.cos(math.radians(lat)))
    data = {
        "point": [lat, lon],
        "square": [[lat - dlat, lon - dlon], [lat + dlat, lon + dlon]],
        "title": title_geom,
        "titlePopup": title_popup,
        "elev": elev,
        "ne": ne,
        "ukpn": grid,
        "osKey": os.environ.get("OS_API_KEY"),
    }
    facts = f"Title: {title_popup.replace('<br>', ' · ')}" if title_geom else "No title boundary found at this point."
    if elev:
        ms = [e["m"] for e in elev]
        if "median_slope_percent" in terrain:
            facts += (
                f" · terrain {terrain['min_m']:.1f}–{terrain['max_m']:.1f} m, slope median "
                f"{terrain['median_slope_percent']}% / p90 {terrain['p90_slope_percent']}% "
                f"({terrain['cells_in_title']} LIDAR cells of {terrain['cell_m']} m)"
            )
        else:
            facts += f" · elevation {min(ms):.0f}–{max(ms):.0f} m over {len(ms)} points (90 m DEM)"

    if grid and grid["substations"]:
        n = grid["substations"][0]
        facts += f"<br>Nearest substation: <b>{n['name']}</b> ({n['kv']} kV, {n['type']}) {n['km']} km away"
        if grid["headroom"]:
            h = grid["headroom"][0]
            facts += (
                f" · nearest headroom record <b>{h['name']}</b>: generation {h['gen_mw']} MW ({h['gen_rag']}), "
                f"demand {h['dem_mw']} MW ({h['dem_rag']})"
            )
        storage = [e for e in grid["ecr"] if e["storage"]]
        facts += (
            f" · {len(grid['ecr'])} registered projects ≥1 MW within {UKPN_RADIUS_M // 1000} km, {len(storage)} storage"
        )
    elif grid:
        facts += "<br>No UKPN / NGED / SSEN substations nearby (Northern Powergrid, ENWL or SPEN area?)"

    out = Path(f"site_report_{lat}_{lon}.html")
    out.write_text(
        f"<!doctype html><meta charset=utf-8><title>Site {lat}, {lon}</title>"
        '<link rel=stylesheet href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">'
        '<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>'
        f"<style>{CSS}</style><h1>Site report: {lat}, {lon}</h1><div class=facts>{facts}</div><div id=map></div>"
        f'<script id=data type="application/json">{json.dumps(data).replace("</", "<\\/")}</script>'
        f"<script>{MAP_JS}</script>{''.join(sections)}",
        encoding="utf-8",
    )
    print("wrote", out, f"({out.stat().st_size // 1024} KB)")
    webbrowser.open(out.resolve().as_uri())


if __name__ == "__main__":
    main()
