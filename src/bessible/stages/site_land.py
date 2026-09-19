"""Site and land constraints assessment stage placeholder."""

from __future__ import annotations

import asyncio
import logging
import os

from pydantic import HttpUrl

from bessible.models import Artifact, NodeInput, SiteLandOutput

log = logging.getLogger(__name__)
LIVE_TIMEOUT_S = 45

DEFAULT_LAND_USE = "Agricultural (Grade 3b)"
DEFAULT_CONSTRAINTS = [
    "Close to secondary road access",
    "Surface water flood risk low (Zone 1)",
    "No SSSI or ecological designations on site",
]


async def site_land(inp: NodeInput) -> SiteLandOutput:
    """Assess land classification, topography, and environmental designations."""
    if os.environ.get("BESSIBLE_LIVE_LAND") == "1":
        try:
            return await asyncio.wait_for(_live_site_land(inp), LIVE_TIMEOUT_S)
        except Exception:
            log.exception("live site_land failed; using placeholder")
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


async def _live_site_land(inp: NodeInput) -> SiteLandOutput:
    """Real land facts: collate the public data for the confirmed position, run the hard checks, adapt."""
    from bessible import events  # ruff: ignore[import-outside-top-level]
    from bessible.location import Coordinates, collate  # ruff: ignore[import-outside-top-level]
    from bessible.possibility.hard import assess  # ruff: ignore[import-outside-top-level]
    from bessible.possibility.models import Proposal  # ruff: ignore[import-outside-top-level]
    from bessible.possibility.pipeline import site_land_output  # ruff: ignore[import-outside-top-level]

    pos = inp.site.position
    events.emit(inp.run_id, "site_land", "Collating flood, designation, farmland, terrain and grid data for the title")
    location = await collate(Coordinates(lat=pos.lat, lon=pos.lon))
    proposal = Proposal(location=location, battery_mw=inp.site.capacity_mw)
    report = assess(proposal)
    events.emit(
        inp.run_id,
        "site_land",
        f"{len(report.checks)} hard checks: {len(report.blockers)} blockers, {len(report.caveats)} caveats",
    )
    return site_land_output(proposal, report, inp.run_id)
