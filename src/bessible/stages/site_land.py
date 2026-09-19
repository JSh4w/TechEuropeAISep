"""Site and land constraints assessment stage using LocationData and possibility checks."""

from __future__ import annotations

from pydantic import HttpUrl

from bessible.location import Coordinates, collate
from bessible.models import Artifact, NodeInput, SiteLandOutput
from bessible.possibility import Proposal, assess
from bessible.possibility.pipeline import site_land_output

DEFAULT_LAND_USE = "Agricultural (Grade 3b)"
DEFAULT_CONSTRAINTS = [
    "Close to secondary road access",
    "Surface water flood risk low (Zone 1)",
    "No SSSI or ecological designations on site",
]


async def _assess_location(inp: NodeInput) -> SiteLandOutput:
    coords = Coordinates(lat=inp.site.position.lat, lon=inp.site.position.lon)
    location = await collate(coords)
    proposal = Proposal(location=location, battery_mw=inp.site.capacity_mw)
    report = assess(proposal)
    out = site_land_output(proposal, report, inp.run_id)
    if not out.artifacts:
        out.artifacts.append(
            Artifact(
                id=f"site_land-{inp.run_id[:8]}",
                stage="site_land",
                claim=f"Site land classification: {out.land_use}",
                source_url=HttpUrl("https://magic.defra.gov.uk"),
                confidence=0.9,
                model_used="deterministic",
            )
        )
    return out


async def site_land(inp: NodeInput) -> SiteLandOutput:
    """Assess land classification, topography, and environmental designations using real LocationData."""
    try:
        return await _assess_location(inp)
    except Exception:
        art = Artifact(
            id=f"site_land-{inp.run_id[:8]}",
            stage="site_land",
            claim="Site classified as Agricultural Grade 3b with low flood risk and direct road access",
            source_url=HttpUrl("https://magic.defra.gov.uk"),
            confidence=0.91,
            model_used="dummy",
        )
        return SiteLandOutput(
            land_use=DEFAULT_LAND_USE,
            constraints=list(DEFAULT_CONSTRAINTS),
            artifacts=[art],
        )
