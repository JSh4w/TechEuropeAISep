"""Postcode geocoding through postcodes.io, with a JSON fixture cache so demo postcodes work offline."""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

import httpx

from bessible.api.postcodes_io import (
    PostcodeLookupRequest,
    PostcodeLookupResponse,
    PostcodeResult,
    PostcodesIoError,
    ReverseGeocodeRequest,
    ReverseGeocodeResponse,
)
from bessible.config import settings

if TYPE_CHECKING:
    from pathlib import Path

TIMEOUT_S = 10.0
_POSTCODE_RE = re.compile(r"^[A-Z]{1,2}\d[A-Z\d]?\d[A-Z]{2}$")


class PostcodeNotFoundError(Exception):
    """The postcode is malformed, unknown or terminated. Retrying will not help."""


def normalise_postcode(postcode: str) -> str:
    """Upper-case and strip spaces, e.g. ``"rh4 1ad"`` -> ``"RH41AD"``."""
    return re.sub(r"\s+", "", postcode).upper()


def format_postcode(postcode: str) -> str:
    """Canonical display form with the space before the 3-character incode, e.g. ``"RH4 1AD"``."""
    norm = normalise_postcode(postcode)
    return f"{norm[:-3]} {norm[-3:]}"


def _cache_path(norm: str) -> Path:
    return settings.data_dir / "fixtures" / "postcodes" / f"{norm}.json"


async def geocode_postcode(postcode: str, *, client: httpx.AsyncClient | None = None) -> PostcodeResult:
    """Look up a UK postcode: the fixture cache first, else postcodes.io (then cached).

    Raises:
        PostcodeNotFoundError: malformed, unknown or terminated postcode, or one without coordinates.
    """
    norm = normalise_postcode(postcode)
    if not _POSTCODE_RE.match(norm):
        msg = f"'{postcode}' is not a valid UK postcode"
        raise PostcodeNotFoundError(msg)

    cache = _cache_path(norm)
    if cache.exists():
        body = json.loads(cache.read_text())
    else:
        req = PostcodeLookupRequest(postcode=norm)
        if client is None:
            async with httpx.AsyncClient(timeout=TIMEOUT_S) as own:
                resp = await own.get(req.url())
        else:
            resp = await client.get(req.url())
        if resp.status_code in {400, 404}:
            err = PostcodesIoError.model_validate(resp.json())
            msg = f"postcodes.io: {err.error} ('{postcode}')"
            raise PostcodeNotFoundError(msg)
        resp.raise_for_status()
        body = resp.json()
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(body))

    result = PostcodeLookupResponse.model_validate(body).result
    if result.latitude is None or result.longitude is None:
        msg = f"postcodes.io has no coordinates for '{postcode}' (crown dependency or unmapped)"
        raise PostcodeNotFoundError(msg)
    return result


async def nearest_postcode(lat: float, lon: float, *, client: httpx.AsyncClient | None = None) -> PostcodeResult | None:
    """The live UK postcode nearest to a point, searching up to 20 km out. None when there is none (not in the UK)."""
    req = ReverseGeocodeRequest(lat=lat, lon=lon, limit=1, widesearch=True)
    if client is None:
        async with httpx.AsyncClient(timeout=TIMEOUT_S) as own:
            resp = await own.get(req.URL, params=req.params())
    else:
        resp = await client.get(req.URL, params=req.params())
    resp.raise_for_status()
    results = ReverseGeocodeResponse.model_validate(resp.json()).result
    return results[0] if results else None
