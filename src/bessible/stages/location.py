"""Location resolution stage: postcode to coordinates or link extraction."""

from __future__ import annotations

from pydantic import HttpUrl

from bessible.geocode import format_postcode, geocode_postcode
from bessible.location.extract import LocationNotFound, resolve_from_link
from bessible.models import Artifact, LocationInput, LocationOutput, Position

POSTCODES_IO_URL = "https://api.postcodes.io/postcodes/"
QUALITY_CONFIDENCE_LIMIT = 4  # postcodes.io positional quality 1-4 is a unit-postcode centroid or better


async def resolve_location(inp: LocationInput) -> LocationOutput:
    """Resolve a postcode or property link to coordinates and canonical postcode.

    If a postcode is provided in the request, it wins and no page is fetched.
    Otherwise, the property link is fetched and location details are extracted.

    Raises:
        LocationNotFound: if extraction fails, no address exists, non-UK, or postcode invalid.
    """
    if inp.request.postcode:
        result = await geocode_postcode(inp.request.postcode)
        postcode = format_postcode(result.postcode)
        assert result.latitude is not None and result.longitude is not None
        pos = Position(lat=result.latitude, lon=result.longitude)

        area = result.admin_district or result.country
        claim = f"Postcode {postcode} geocodes to ({pos.lat:.4f}, {pos.lon:.4f}) in {area}"
        art = Artifact(
            id=f"location-{inp.run_id[:8]}",
            stage="location",
            claim=claim,
            source_url=HttpUrl(f"{POSTCODES_IO_URL}{result.postcode.replace(' ', '')}"),
            confidence=0.95 if result.quality <= QUALITY_CONFIDENCE_LIMIT else 0.6,
            model_used="postcodes.io",
        )
        return LocationOutput(postcode=postcode, position=pos, artifacts=[art])

    target_url = inp.request.property_url or inp.request.link
    if target_url is None:
        msg = "No property link or postcode was provided. Please pass --postcode."
        raise LocationNotFound(msg)

    return await resolve_from_link(str(target_url), inp.run_id)
