"""Tests verifying stage integration and failure modes for location resolution."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import HttpUrl
from pydantic_ai.models.test import TestModel
from temporalio.exceptions import ApplicationError

from bessible import activities
from bessible.api.postcodes_io import PostcodeResult, ReverseGeocodeResponse
from bessible.location.extract import ExtractedLocation, LocationNotFound
from bessible.location.fetch import PageUnavailable, page_cache_path
from bessible.models import AssessmentRequest, LocationInput
from bessible.stages.location import resolve_location

if TYPE_CHECKING:
    from bessible.models import EncryptedCredentials
    from tests.conftest import FakeGemini


@pytest.mark.anyio
async def test_postcode_given_wins_and_fetches_nothing():
    """Verify that when both link and postcode are given, the postcode wins and no fetch is made."""
    req = AssessmentRequest(
        property_url=HttpUrl("https://example.com/property-never-fetched"),
        postcode="RH4 1AD",
    )
    inp = LocationInput(run_id="run-postcode-wins", request=req)

    with patch("bessible.location.fetch.fetch_page_text", new_callable=AsyncMock) as mock_fetch:
        loc = await resolve_location(inp)
        assert loc.postcode == "RH4 1AD"
        assert mock_fetch.call_count == 0


@pytest.mark.anyio
async def test_page_with_no_address_fails_with_postcode_hint(monkeypatch, tmp_path):
    """Verify a page with no address fails with an error message that mentions --postcode."""
    monkeypatch.setattr("bessible.config.settings.data_dir", tmp_path)
    url = "https://example.com/no-address-page"

    cache_file = page_cache_path(url)
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps({"url": url, "text": "Contact us for more details."}))

    req = AssessmentRequest(property_url=HttpUrl(url))
    inp = LocationInput(run_id="run-no-address", request=req)

    test_model = TestModel(
        custom_output_args=ExtractedLocation(
            address=None,
            postcode=None,
            confidence=0.0,
        )
    )

    with pytest.raises(LocationNotFound, match="--postcode"):
        await resolve_location(inp, model=test_model)


@pytest.mark.anyio
async def test_activity_wrapper_maps_location_not_found_to_non_retryable(
    fake_gemini: FakeGemini, run_credentials: EncryptedCredentials
):
    """Verify Temporal activity wrapper catches LocationNotFound and raises non-retryable ApplicationError."""
    req = AssessmentRequest(property_url=HttpUrl("https://example.com/not-found"), credentials=run_credentials)
    inp = LocationInput(run_id="run-activity-test", request=req)

    with patch(
        "bessible.stages.location.resolve_location",
        side_effect=LocationNotFound("Failed. Use --postcode."),
    ):
        with pytest.raises(ApplicationError) as exc_info:
            await activities.resolve_location(inp)

        err = exc_info.value
        assert err.non_retryable is True
        assert err.type == "LocationNotFound"
        assert "--postcode" in str(err)


@pytest.mark.anyio
async def test_activity_wrapper_maps_page_unavailable_to_non_retryable(
    fake_gemini: FakeGemini, run_credentials: EncryptedCredentials
):
    """Verify Temporal activity wrapper catches PageUnavailable and raises non-retryable ApplicationError."""
    req = AssessmentRequest(property_url=HttpUrl("https://example.com/offline-page"), credentials=run_credentials)
    inp = LocationInput(run_id="run-unavailable-test", request=req)

    with patch(
        "bessible.stages.location.resolve_location",
        side_effect=PageUnavailable("HTTP 500 error"),
    ):
        with pytest.raises(ApplicationError) as exc_info:
            await activities.resolve_location(inp)

        err = exc_info.value
        assert err.non_retryable is True
        assert err.type == "PageUnavailable"


def _dorking_nearest() -> PostcodeResult:
    body = json.loads((Path(__file__).parent.parent / "api/fixtures/postcodes_io_reverse_dorking.json").read_text())
    return ReverseGeocodeResponse.model_validate(body).result[0]


@pytest.mark.anyio
async def test_pin_alone_is_a_valid_request_and_keeps_its_exact_position():
    """A map pin needs no postcode: the site stays at the pin and the nearest postcode only labels it."""
    req = AssessmentRequest(position=[-0.3311, 51.2335])  # [lon, lat], as the web sends it
    inp = LocationInput(run_id="run-pin", request=req)

    with patch("bessible.stages.location.nearest_postcode", AsyncMock(return_value=_dorking_nearest())) as nearest:
        loc = await resolve_location(inp)

    nearest.assert_awaited_once_with(51.2335, -0.3311)
    assert (loc.position.lat, loc.position.lon) == (51.2335, -0.3311)
    assert loc.postcode == "RH4 1AD"
    assert "Map pin" in loc.artifacts[0].claim
    assert "Mole Valley" in loc.artifacts[0].claim


@pytest.mark.anyio
async def test_pin_wins_over_postcode():
    """A pin is more exact than a postcode centroid, so it wins when both are sent."""
    req = AssessmentRequest(postcode="SE1 7PB", position={"lat": 51.2335, "lon": -0.3311})
    inp = LocationInput(run_id="run-pin-wins", request=req)

    with (
        patch("bessible.stages.location.nearest_postcode", AsyncMock(return_value=_dorking_nearest())),
        patch("bessible.stages.location.geocode_postcode", AsyncMock()) as geocode,
    ):
        loc = await resolve_location(inp)

    geocode.assert_not_awaited()
    assert loc.position.lat == 51.2335


@pytest.mark.anyio
async def test_pin_outside_the_uk_fails():
    """A pin with no UK postcode within 20 km is not a UK site."""
    req = AssessmentRequest(position={"lat": 48.8566, "lon": 2.3522})
    inp = LocationInput(run_id="run-pin-paris", request=req)

    with (
        patch("bessible.stages.location.nearest_postcode", AsyncMock(return_value=None)),
        pytest.raises(LocationNotFound, match="Only UK sites"),
    ):
        await resolve_location(inp)
