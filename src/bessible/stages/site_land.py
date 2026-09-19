"""Site and land constraints assessment stage placeholder."""

from __future__ import annotations

import asyncio

from pydantic import HttpUrl

from bessible.models import Artifact, NodeInput, SiteLandOutput

DEFAULT_LAND_USE = "Agricultural (Grade 3b)"
DEFAULT_CONSTRAINTS = [
    "Close to secondary road access",
    "Surface water flood risk low (Zone 1)",
    "No SSSI or ecological designations on site",
]


async def site_land(inp: NodeInput) -> SiteLandOutput:
    """Assess land classification, topography, and environmental designations."""
    await asyncio.sleep(0)

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
