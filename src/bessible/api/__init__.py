"""Pydantic models of the external data APIs: one module per endpoint (data source), exactly as the API speaks.

These classes model the wire format only: every request param and every response field, nothing derived.
Responses forbid unknown fields, so a new upstream field fails loudly (our model is stale). The refined,
BESS-specific models that pick and transform what we need are built on top of these, in `bessible.location`.

Every module has the same layout:

    docstring   where the API is accessed from, auth, and notes verified against the live service
    constants   base URL, resource ids
    1. Request              <Name>Request: `.params()` gives the wire params, `URL` / `.url()` the address
    2. Response             <Name>Response / <Name>Error
    3. Response sub-models  the objects nested inside a response (rows, features, properties)
    4. Not from the API     request builders (`x_at_point`, `near`), registries, parsers, transforms

Models are verified against real responses saved in `tests/api/fixtures`.

Location
    postcodes_io       Postcode <-> coordinate; admin district, parish, constituency, ONS codes, rural/urban class.
    nominatim          OpenStreetMap reverse geocode: a human-readable address / place name for a coordinate.

The site and its constraints
    planning_data      planning.data.gov.uk entities at a point: the title boundary polygon (the site), planning
                       authority and local plan, green belt, heritage, flood zone, ALC grade, Article 4, brownfield...
                       43 typed datasets. Also the dataset catalogue.
    natural_england    ArcGIS layers with geometry: agricultural land class (incl. post-1988 3a/3b surveys), SSSI and
                       impact risk zones, SAC / SPA / Ramsar, AONB, national parks, ancient woodland, reserves.
    ea_flood           Environment Agency Flood Map for Planning: Flood Zone 2 / 3 polygons at or near a point
                       (no features = Zone 1).

Terrain
    ea_lidar           Environment Agency LIDAR 1 m terrain model (England) as a GeoTIFF for a bounding box; decoded
                       to a height grid for min / max height and slope.
    open_meteo         Elevation for up to 100 points from a 90 m DEM; the fallback outside LIDAR coverage.

Grid: distribution network operators (substations, headroom, competing projects)
    ukpn               UK Power Networks (London, South East, East): substations, capacity heatmap (MW headroom + RAG),
                       embedded capacity register (>= 1 MW), 132 / 33 kV overhead lines. Spatial queries. Key.
    nged               National Grid Electricity Distribution (South West, South Wales, Midlands): network capacity
                       map (headroom + RAG per primary / BSP), embedded capacity register. No spatial query. Token.
    ssen_distribution  SSEN Distribution (central southern England, north Scotland): headroom dashboard (headroom,
                       RAG, named constraint, planned reinforcement), embedded capacity register (>= 1 MW),
                       overhead lines 22-132 kV. No spatial query. No key, browser User-Agent.
    sp_energy          SP Energy Networks (central & southern Scotland, Merseyside, North Wales, Cheshire): capacity
                       heatmaps (MW headroom + RAG), embedded capacity register (>= 1 MW), overhead lines, substations.
                       Spatial queries. Key.

Grid: transmission
    ssen               SSEN Transmission (north Scotland only): 132 / 275 / 400 kV substations and overhead lines,
                       its TEC and embedded registers. Spatial queries. Key.
    neso               National Energy System Operator: the GB TEC register (transmission connection queue), matched
                       to a site by grid supply point name; DNO licence area boundary files. 2 requests/minute.

Shared
    base               ApiRequest / ApiResponse (forbid unknown fields) and NullMarkerResponse ("" / "N/A" -> None).
    ckan               CKAN action API envelope, package and datastore models (neso, nged, ssen_distribution).
    opendatasoft       Opendatasoft Explore v2.1 records request, envelope, geo fields, DatasetSpec
                       (ukpn, ssen, sp_energy).
    geo                distance_km / nearest, for the portals without a spatial query.
"""
