"""Tests verifying stage integration and failure modes for location resolution."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import HttpUrl
from pydantic_ai.models.test import TestModel
from temporalio.exceptions import ApplicationError

from bessible import activities
from bessible.location.extract import ExtractedLocation, LocationNotFound
from bessible.location.fetch import PageUnavailable, page_cache_path
from bessible.models import AssessmentRequest, LocationInput
from bessible.stages.location import resolve_location


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

    with (
        patch("bessible.location.extract.gemini_model", return_value=test_model),
        pytest.raises(LocationNotFound, match="--postcode"),
    ):
        await resolve_location(inp)


@pytest.mark.anyio
async def test_activity_wrapper_maps_location_not_found_to_non_retryable():
    """Verify Temporal activity wrapper catches LocationNotFound and raises non-retryable ApplicationError."""
    req = AssessmentRequest(property_url=HttpUrl("https://example.com/not-found"))
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
async def test_activity_wrapper_maps_page_unavailable_to_non_retryable():
    """Verify Temporal activity wrapper catches PageUnavailable and raises non-retryable ApplicationError."""
    req = AssessmentRequest(property_url=HttpUrl("https://example.com/offline-page"))
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
