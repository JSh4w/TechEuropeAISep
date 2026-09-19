"""Location resolution stage: postcode to coordinates through postcodes.io."""

from __future__ import annotations

from pydantic import HttpUrl

from bessible.geocode import format_postcode, geocode_postcode
from bessible.models import Artifact, LocationInput, LocationOutput, Position

# Placeholder for link-only requests until add-link-location-extraction lands (a postcode in a UKPN area).
PLACEHOLDER_POSTCODE = "RH4 1AD"
POSTCODES_IO_URL = "https://api.postcodes.io/postcodes/"
QUALITY_CONFIDENCE_LIMIT = 4  # postcodes.io positional quality 1-4 is a unit-postcode centroid or better


async def resolve_location(inp: LocationInput) -> LocationOutput:
    """Resolve a postcode (or, for now, a placeholder for property links) to coordinates and canonical postcode."""
    requested = inp.request.postcode or PLACEHOLDER_POSTCODE
    result = await geocode_postcode(requested)
    postcode = format_postcode(result.postcode)
    pos = Position(lat=result.latitude, lon=result.longitude)  # type: ignore[arg-type]  # geocode_postcode guarantees both

    if inp.request.postcode:
        area = result.admin_district or result.country
        claim = f"Postcode {postcode} geocodes to ({pos.lat:.4f}, {pos.lon:.4f}) in {area}"
    else:
        claim = (
            f"Placeholder location {postcode} at ({pos.lat:.4f}, {pos.lon:.4f}): "
            "address extraction from the property link is not implemented, pass --postcode"
        )
    art = Artifact(
        id=f"location-{inp.run_id[:8]}",
        stage="location",
        claim=claim,
        source_url=HttpUrl(f"{POSTCODES_IO_URL}{result.postcode.replace(' ', '')}"),
        confidence=(0.95 if inp.request.postcode else 0.3) if result.quality <= QUALITY_CONFIDENCE_LIMIT else 0.6,
        model_used="postcodes.io",
    )
    return LocationOutput(postcode=postcode, position=pos, artifacts=[art])
