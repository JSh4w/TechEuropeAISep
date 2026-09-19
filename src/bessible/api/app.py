"""FastAPI HTTP Server for Bessible."""

from __future__ import annotations

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from bessible.api import capacity, events, runs
from bessible.config import settings

app = FastAPI(
    title="Bessible API",
    description="HTTP API and SSE Events Bridge for BESS site assessment workflow",
    version="0.1.0",
)

# Enable CORS for the Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include route modules
app.include_router(runs.router)
app.include_router(capacity.router)
app.include_router(events.router)


@app.get("/data/areas.geojson", tags=["data"])
async def get_areas_geojson() -> Response:
    """Serve the UKPN serving areas GeoJSON or an empty FeatureCollection if not yet ingested."""
    candidates = [
        settings.data_dir / "ukpn" / "areas.geojson",
        settings.data_dir / "areas.geojson",
        settings.data_dir.parent / "data" / "ukpn" / "areas.geojson",
    ]
    for path in candidates:
        if path.exists():
            return Response(content=path.read_text(encoding="utf-8"), media_type="application/geo+json")

    return JSONResponse(content={"type": "FeatureCollection", "features": []})


@app.get("/inspire", tags=["data"])
async def get_inspire_parcels(_bbox: str | None = None) -> Response:
    """Proxy/cached HM Land Registry INSPIRE index polygons."""
    # Return empty FeatureCollection or cached demo polygons
    return JSONResponse(content={"type": "FeatureCollection", "features": []})


@app.get("/health", tags=["system"])
async def health_check() -> dict[str, str]:
    """Basic health check endpoint."""
    return {"status": "ok"}
